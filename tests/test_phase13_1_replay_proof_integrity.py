"""Phase 13.1 -- Replay and Proof integrity fixes.

Two gaps found in review of Phases 12/13:

1. Declared decisions with no evaluator were silently skipped, so a case
   could come back "passed" having only partially evaluated the process.
   The engine now records `unsupported_decisions`/`decision_coverage_rate`
   and forces `needs_clarification` when coverage is incomplete; a proof
   built on incomplete coverage is capped at `needs_changes`, never
   `eligible_for_shadow`.
2. `ProcessReplay`'s immutable-after-freeze listener didn't cover
   `ProcessReplayCase` -- a frozen replay's header couldn't change but its
   case rows still could. Case rows now reject update/delete once their
   parent replay is frozen.
"""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.model_packages.replay import ProcessReplayCase
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.fake_generator import build_fake_quote_to_order_ocel
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.processes.registry import ProcessRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


def _identity(tenant_id: str, role: str = "admin") -> dict[str, str]:
    suffix = uuid4().hex
    user_id = f"integrity-user-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Integrity user"))
    db.add(
        IdentityMembership(
            id=f"integrity-membership-{suffix}",
            tenant_id=tenant_id,
            user_id=user_id,
            role_name=role,
            status="active",
        )
    )
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'integrity-auth')}"}


def _register_process(suffix: str) -> str:
    process_key = f"integrity_process_{suffix}"
    db = SessionLocal()
    try:
        base = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        ProcessRegistry(db).register_yaml(base)
    finally:
        db.close()
    return process_key


def _create_replay(client: TestClient, headers: dict, process_key: str) -> dict:
    response = client.post(
        f"/v1/processes/{process_key}/versions/1.0.0/replays",
        headers=headers,
        json={"object_type": "sales_order"},
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_case_with_unsupported_decision_needs_clarification_not_silent_pass(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "integrity-auth")
    init_db()
    tenant_id = f"integrity-tenant-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    object_key = f"so-confirmed-{uuid4().hex[:8]}"

    db = SessionLocal()
    try:
        OcelEventService(db).import_ocel(
            tenant_id=tenant_id,
            document=build_fake_quote_to_order_ocel(
                tenant_id=tenant_id, object_key=object_key, formula_valid=True, include_confirmation=True
            ),
            source="test",
        )
    finally:
        db.close()

    client = TestClient(app)
    headers = _identity(tenant_id)
    replay = _create_replay(client, headers, process_key)

    cases_response = client.get(f"/v1/replays/{replay['id']}/cases", headers=headers)
    assert cases_response.status_code == 200, cases_response.text
    cases = {c["case_id"]: c for c in cases_response.json()}
    case = cases[object_key]

    # approval_gate applies to sales.order.confirmed (present in this case's
    # trace) but has no evaluator -- the case must be inconclusive, not a
    # silent "passed" that hides the fact only formula_guard actually ran.
    assert case["status"] == "needs_clarification"
    assert "approval_gate" in case["unsupported_decisions"]
    assert case["decision_coverage_rate"] < 1.0
    assert case["declared_decision_count"] == 2
    assert case["evaluated_decision_count"] == 1
    # The decision that DID have an evaluator still ran and is visible.
    assert any(item["decision_name"] == "formula_guard" for item in case["decision_trace"])


def test_case_without_unsupported_decisions_has_full_coverage(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "integrity-auth")
    init_db()
    tenant_id = f"integrity-tenant-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    object_key = f"so-plain-{uuid4().hex[:8]}"

    db = SessionLocal()
    try:
        OcelEventService(db).import_ocel(
            tenant_id=tenant_id,
            document=build_fake_quote_to_order_ocel(tenant_id=tenant_id, object_key=object_key, formula_valid=True),
            source="test",
        )
    finally:
        db.close()

    client = TestClient(app)
    headers = _identity(tenant_id)
    replay = _create_replay(client, headers, process_key)

    cases = {c["case_id"]: c for c in client.get(f"/v1/replays/{replay['id']}/cases", headers=headers).json()}
    case = cases[object_key]
    assert case["status"] == "passed"
    assert case["unsupported_decisions"] == []
    assert case["decision_coverage_rate"] == 1.0


def test_frozen_replay_case_rejects_update_and_delete(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "integrity-auth")
    init_db()
    tenant_id = f"integrity-tenant-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    object_key = f"so-freeze-{uuid4().hex[:8]}"

    db = SessionLocal()
    try:
        OcelEventService(db).import_ocel(
            tenant_id=tenant_id,
            document=build_fake_quote_to_order_ocel(tenant_id=tenant_id, object_key=object_key, formula_valid=True),
            source="test",
        )
    finally:
        db.close()

    client = TestClient(app)
    headers = _identity(tenant_id)
    replay = _create_replay(client, headers, process_key)

    freeze_response = client.post(f"/v1/replays/{replay['id']}/freeze", headers=headers)
    assert freeze_response.status_code == 200, freeze_response.text

    db = SessionLocal()
    try:
        case = db.query(ProcessReplayCase).filter_by(tenant_id=tenant_id, replay_id=replay["id"]).one()
        case.status = "tampered"
        with pytest.raises(ValueError, match="frozen_replay_case_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()

    db = SessionLocal()
    try:
        case = db.query(ProcessReplayCase).filter_by(tenant_id=tenant_id, replay_id=replay["id"]).one()
        db.delete(case)
        with pytest.raises(ValueError, match="frozen_replay_case_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_proof_requires_both_replays_frozen_not_merely_completed(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "integrity-auth")
    init_db()
    tenant_id = f"integrity-tenant-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)
    object_key = f"so-proof-gate-{uuid4().hex[:8]}"

    db = SessionLocal()
    try:
        OcelEventService(db).import_ocel(
            tenant_id=tenant_id,
            document=build_fake_quote_to_order_ocel(tenant_id=tenant_id, object_key=object_key, formula_valid=True),
            source="test",
        )
    finally:
        db.close()

    client = TestClient(app)
    headers = _identity(tenant_id)
    baseline = _create_replay(client, headers, process_key)
    candidate = _create_replay(client, headers, process_key)

    # Neither replay is frozen yet -- proof generation must be rejected even
    # though both are "completed".
    response = client.post(
        f"/v1/replays/{candidate['id']}/proofs",
        headers=headers,
        json={"baseline_replay_id": baseline["id"], "benchmark_version": "erpriskbench-1.0.0"},
    )
    assert response.status_code == 400, response.text

    assert client.post(f"/v1/replays/{baseline['id']}/freeze", headers=headers).status_code == 200
    response = client.post(
        f"/v1/replays/{candidate['id']}/proofs",
        headers=headers,
        json={"baseline_replay_id": baseline["id"], "benchmark_version": "erpriskbench-1.0.0"},
    )
    assert response.status_code == 400, response.text

    assert client.post(f"/v1/replays/{candidate['id']}/freeze", headers=headers).status_code == 200
    response = client.post(
        f"/v1/replays/{candidate['id']}/proofs",
        headers=headers,
        json={"baseline_replay_id": baseline["id"], "benchmark_version": "erpriskbench-1.0.0"},
    )
    assert response.status_code == 201, response.text


def test_incomplete_decision_coverage_caps_proof_below_eligible_for_shadow(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "integrity-auth")
    init_db()
    tenant_id = f"integrity-tenant-{uuid4().hex}"
    process_key = _register_process(uuid4().hex)

    db = SessionLocal()
    try:
        service = OcelEventService(db)
        for label in ("baseline", "candidate"):
            service.import_ocel(
                tenant_id=tenant_id,
                document=build_fake_quote_to_order_ocel(
                    tenant_id=tenant_id,
                    object_key=f"so-coverage-{label}-{uuid4().hex[:8]}",
                    formula_valid=True,
                    include_confirmation=True,
                ),
                source="test",
            )
    finally:
        db.close()

    client = TestClient(app)
    headers = _identity(tenant_id)
    baseline = _create_replay(client, headers, process_key)
    candidate = _create_replay(client, headers, process_key)
    client.post(f"/v1/replays/{baseline['id']}/freeze", headers=headers)
    client.post(f"/v1/replays/{candidate['id']}/freeze", headers=headers)

    response = client.post(
        f"/v1/replays/{candidate['id']}/proofs",
        headers=headers,
        json={"baseline_replay_id": baseline["id"], "benchmark_version": "erpriskbench-1.0.0"},
    )
    assert response.status_code == 201, response.text
    proof = response.json()
    assert proof["recommendation"] in ("needs_changes", "reject")
    assert proof["recommendation"] != "eligible_for_shadow"
