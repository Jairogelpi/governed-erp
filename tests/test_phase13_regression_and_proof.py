from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.model_packages.replay import ProcessReplay, ProcessReplayCase
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.processes.registry import ProcessRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def _identity(tenant_id: str, role: str = "admin") -> dict[str, str]:
    suffix = uuid4().hex
    user_id = f"proof-user-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Proof user"))
    db.add(
        IdentityMembership(
            id=f"proof-membership-{suffix}",
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role,
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'proof-auth')}"}


def _register_process(suffix: str) -> str:
    process_key = f"proof_process_{suffix}"
    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()
    return process_key


def _decision_trace(*, outcome: str, risk_level: str = "R2") -> list[dict]:
    return [
        {
            "decision_name": "formula_guard",
            "applies_to": "sales.quote.reviewed",
            "outcome": outcome,
            "policy_id": "formula_guard",
            "policy_version": "1.0.0",
            "summary": f"formula_guard {outcome}",
            "risk_level": risk_level,
        }
    ]


def _violations(codes: list[str]) -> list[dict]:
    return [{"code": code, "message": code, "evidence": {}} for code in codes]


def _make_replay(*, tenant_id: str, process_key: str, cases: dict[str, dict]) -> ProcessReplay:
    """`cases`: case_id -> {status, outcome, violation_codes}."""

    db = SessionLocal()
    try:
        replay = ProcessReplay(
            id=f"replay_{uuid4().hex}",
            tenant_id=tenant_id,
            process_key=process_key,
            version="1.0.0",
            object_type="sales_order",
            status="completed",
            policy_version="1.0.0",
            connector_simulator_version="fake-blocked-by-construction/1",
            case_count=len(cases),
            completed_at=datetime.now(timezone.utc),
        )
        db.add(replay)
        db.flush()
        for case_id, spec in cases.items():
            status = spec["status"]
            decision_trace = [] if status == "needs_clarification" else _decision_trace(outcome=spec["outcome"])
            violations = _violations(spec.get("violation_codes", []))
            db.add(
                ProcessReplayCase(
                    id=f"replaycase_{uuid4().hex}",
                    tenant_id=tenant_id,
                    replay_id=replay.id,
                    case_id=case_id,
                    status=status,
                    decision_trace_json=json.dumps(decision_trace),
                    predicted_effects_json="[]",
                    safety_violations_json=json.dumps(violations),
                    regressions_json="[]",
                    metrics_json="{}",
                    deterministic_trace_hash=f"hash_{case_id}_{status}_{spec.get('outcome', '')}",
                )
            )
        db.commit()
        db.refresh(replay)
        return replay
    finally:
        db.close()


def _create_proof(client: TestClient, headers: dict, *, candidate_replay_id: str, baseline_replay_id: str) -> dict:
    response = client.post(
        f"/v1/replays/{candidate_replay_id}/proofs",
        headers=headers,
        json={"baseline_replay_id": baseline_replay_id, "benchmark_version": "erpriskbench-1.0.0"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_new_unsafe_effect_is_critical_and_blocks_recommendation(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "proof-auth")
    init_db()
    tenant_id = f"proof-critical-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)

    # Baseline blocked this case (unsafe effect caught); candidate now allows it.
    baseline = _make_replay(
        tenant_id=tenant_id,
        process_key=process_key,
        cases={"caseA": {"status": "failed", "outcome": "block", "violation_codes": ["formula_mismatch"]}},
    )
    candidate = _make_replay(
        tenant_id=tenant_id,
        process_key=process_key,
        cases={"caseA": {"status": "passed", "outcome": "allow"}},
    )

    headers = _identity(tenant_id)
    client = TestClient(app)
    proof = _create_proof(client, headers, candidate_replay_id=candidate.id, baseline_replay_id=baseline.id)

    critical = [r for r in proof["regressions"] if r["severity"] == "critical"]
    assert critical == [{"severity": "critical", "category": "new_unsafe_effect", "count": 1}]
    assert proof["safety_summary"]["critical_regressions"] == 1
    assert proof["recommendation"] == "reject"
    assert any("critical" in item for item in proof["recommendation_basis"])


def test_false_block_is_low_severity_not_critical(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "proof-auth")
    init_db()
    tenant_id = f"proof-falseblock-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)

    baseline = _make_replay(
        tenant_id=tenant_id,
        process_key=process_key,
        cases={"caseB": {"status": "passed", "outcome": "allow"}},
    )
    candidate = _make_replay(
        tenant_id=tenant_id,
        process_key=process_key,
        cases={"caseB": {"status": "failed", "outcome": "block", "violation_codes": ["formula_mismatch"]}},
    )

    headers = _identity(tenant_id)
    client = TestClient(app)
    proof = _create_proof(client, headers, candidate_replay_id=candidate.id, baseline_replay_id=baseline.id)

    severities = {r["severity"] for r in proof["regressions"]}
    assert "critical" not in severities
    assert {"severity": "low", "category": "false_block", "count": 1} in proof["regressions"]
    assert proof["safety_summary"]["critical_regressions"] == 0
    # No critical regression and full evidence completeness -> best achievable tier.
    assert proof["recommendation"] == "eligible_for_shadow"


def test_clean_proof_is_eligible_for_shadow_and_never_higher(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "proof-auth")
    init_db()
    tenant_id = f"proof-clean-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)

    cases = {
        "caseC": {"status": "passed", "outcome": "allow"},
        "caseD": {"status": "passed", "outcome": "allow"},
    }
    baseline = _make_replay(tenant_id=tenant_id, process_key=process_key, cases=cases)
    candidate = _make_replay(tenant_id=tenant_id, process_key=process_key, cases=cases)

    headers = _identity(tenant_id)
    client = TestClient(app)
    proof = _create_proof(client, headers, candidate_replay_id=candidate.id, baseline_replay_id=baseline.id)

    assert proof["regressions"] == []
    assert proof["recommendation"] == "eligible_for_shadow"
    assert proof["recommendation"] not in ("eligible_for_canary", "eligible_for_promotion")
    assert proof["reproducibility_summary"]["deterministic"] is True
    assert len(proof["limitations"]) >= 2


def test_proof_is_immutable():
    init_db()
    tenant_id = f"proof-immutable-{uuid4().hex}"
    process_key = f"proof_immutable_{uuid4().hex}"
    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()

    baseline = _make_replay(
        tenant_id=tenant_id, process_key=process_key, cases={"caseE": {"status": "passed", "outcome": "allow"}}
    )
    candidate = _make_replay(
        tenant_id=tenant_id, process_key=process_key, cases={"caseE": {"status": "passed", "outcome": "allow"}}
    )

    from erpguard.domain.proofs.service import ProofService

    db = SessionLocal()
    try:
        row = ProofService(db).generate_proof(
            tenant_id=tenant_id,
            baseline_replay_id=baseline.id,
            candidate_replay_id=candidate.id,
            benchmark_version="erpriskbench-1.0.0",
        )
        row.recommendation = "eligible_for_promotion"
        with pytest.raises(ValueError, match="proof_of_improvement_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_content_hash_is_deterministic_and_changes_with_content():
    init_db()
    tenant_id = f"proof-hash-{uuid4().hex}"
    process_key = f"proof_hash_{uuid4().hex}"
    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()

    cases = {"caseF": {"status": "passed", "outcome": "allow"}}
    baseline = _make_replay(tenant_id=tenant_id, process_key=process_key, cases=cases)
    candidate1 = _make_replay(tenant_id=tenant_id, process_key=process_key, cases=cases)
    candidate2 = _make_replay(
        tenant_id=tenant_id,
        process_key=process_key,
        cases={"caseF": {"status": "failed", "outcome": "block", "violation_codes": ["x"]}},
    )

    from erpguard.domain.proofs.service import ProofService

    db = SessionLocal()
    try:
        proof1 = ProofService(db).generate_proof(
            tenant_id=tenant_id,
            baseline_replay_id=baseline.id,
            candidate_replay_id=candidate1.id,
            benchmark_version="v1",
        )
        proof2 = ProofService(db).generate_proof(
            tenant_id=tenant_id,
            baseline_replay_id=baseline.id,
            candidate_replay_id=candidate2.id,
            benchmark_version="v1",
        )
        assert proof1.content_hash != proof2.content_hash
    finally:
        db.close()


def test_proof_api_is_tenant_scoped(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "proof-auth")
    init_db()
    process_key = _register_process(uuid4().hex)
    tenant_a = f"proof-tenant-a-{uuid4().hex}"
    tenant_b = f"proof-tenant-b-{uuid4().hex}"

    cases = {"caseG": {"status": "passed", "outcome": "allow"}}
    baseline = _make_replay(tenant_id=tenant_a, process_key=process_key, cases=cases)
    candidate = _make_replay(tenant_id=tenant_a, process_key=process_key, cases=cases)

    headers_a = _identity(tenant_a)
    headers_b = _identity(tenant_b)
    client = TestClient(app)

    proof = _create_proof(client, headers_a, candidate_replay_id=candidate.id, baseline_replay_id=baseline.id)
    assert client.get(f"/v1/proofs/{proof['id']}", headers=headers_b).status_code == 404
    assert client.get(f"/v1/proofs/{proof['id']}", headers=headers_a).status_code == 200
