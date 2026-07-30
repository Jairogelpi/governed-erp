from __future__ import annotations

import ast
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.candidate import ProcessCandidate
from erpguard.db.model_packages.execution import ExecutionRun
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.model_packages.proof import ProcessProof
from erpguard.db.model_packages.replay import ProcessReplay
from erpguard.db.model_packages.shadow import (
    ShadowCaseResult,
    ShadowDeployment,
    ShadowFeedRun,
    ShadowOutcomeObservation,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.fake_generator import _fake_sales_order
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.processes.candidate_integrity import stable_digest
from erpguard.domain.processes.models import ProcessDefinitionDocument
from erpguard.domain.processes.registry import ProcessRegistry


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "policies" / "processes" / "quote_to_order_v1.yaml"


@dataclass(frozen=True)
class SeededCandidate:
    candidate_id: str
    proof_id: str
    process_key: str
    base_version: str
    candidate_version: str


def _identity(tenant_id: str, role: str = "admin") -> dict[str, str]:
    suffix = uuid4().hex
    user_id = f"shadow-user-{suffix}"
    db = SessionLocal()
    try:
        db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Shadow reviewer"))
        db.add(
            IdentityMembership(
                id=f"shadow-membership-{suffix}",
                tenant_id=tenant_id,
                user_id=user_id,
                role_name=role,
                status="active",
            )
        )
        db.commit()
    finally:
        db.close()
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'shadow-auth')}"}


def _seed_shadow_eligible_candidate(
    *,
    tenant_id: str,
    remove_formula_guard: bool = False,
    recommendation: str = "eligible_for_shadow",
) -> SeededCandidate:
    suffix = uuid4().hex
    process_key = f"shadow_process_{suffix}"
    candidate_version = "18.0.0"
    now = datetime.now(timezone.utc)
    db = SessionLocal()
    try:
        source = FIXTURE.read_text(encoding="utf-8").replace("quote_to_order", process_key)
        active_row = ProcessRegistry(db).register_yaml(source)
        active = ProcessDefinitionDocument.model_validate_json(active_row.definition_json)
        candidate_document = active.model_copy(
            update={
                "version": candidate_version,
                "decisions": (
                    [decision for decision in active.decisions if decision.name != "formula_guard"]
                    if remove_formula_guard
                    else active.decisions
                ),
            }
        )
        if remove_formula_guard:
            candidate_document = candidate_document.model_copy(
                update={
                    "policies": [
                        policy for policy in active.policies if policy.decision != "formula_guard"
                    ]
                }
            )
        candidate_json = candidate_document.model_dump_json()
        candidate = ProcessCandidate(
            id=f"candidate_{suffix}",
            tenant_id=tenant_id,
            process_key=process_key,
            base_version=active.version,
            candidate_version=candidate_version,
            status="submitted",
            patch_json="{}",
            evidence_json="[]",
            proposal_json="{}",
            base_definition_digest=stable_digest(active.model_dump(mode="json")),
            patch_digest=stable_digest({}),
            candidate_definition_json=candidate_json,
            candidate_definition_digest=stable_digest(
                candidate_document.model_dump(mode="json")
            ),
            validation_status="valid",
            created_by="shadow-test",
            submitted_at=now,
        )
        baseline = ProcessReplay(
            id=f"replay_baseline_{suffix}",
            tenant_id=tenant_id,
            process_key=process_key,
            version=active.version,
            object_type="sales_order",
            status="frozen",
            policy_version="1.0.0",
            connector_simulator_version="fake-blocked-by-construction/1",
            case_count=0,
            completed_at=now,
            frozen_at=now,
        )
        candidate_replay = ProcessReplay(
            id=f"replay_candidate_{suffix}",
            tenant_id=tenant_id,
            process_key=process_key,
            version=candidate_version,
            object_type="sales_order",
            status="frozen",
            policy_version="1.0.0",
            connector_simulator_version="fake-blocked-by-construction/1",
            case_count=0,
            completed_at=now,
            frozen_at=now,
        )
        proof = ProcessProof(
            id=f"proof_{suffix}",
            tenant_id=tenant_id,
            baseline_replay_id=baseline.id,
            candidate_replay_id=candidate_replay.id,
            dataset_version="shadow-test-dataset/1",
            benchmark_version="erpriskbench-1.0.0",
            metric_comparisons_json="[]",
            regressions_json="[]",
            safety_summary_json="{}",
            reproducibility_summary_json='{"deterministic":true}',
            evidence_refs_json="[]",
            recommendation=recommendation,
            recommendation_basis_json='["test fixture"]',
            limitations_json='["synthetic fixture"]',
            content_hash=stable_digest({"candidate": candidate.id, "recommendation": recommendation}),
        )
        db.add_all([candidate, baseline, candidate_replay, proof])
        db.commit()
        return SeededCandidate(
            candidate_id=candidate.id,
            proof_id=proof.id,
            process_key=candidate.process_key,
            base_version=candidate.base_version,
            candidate_version=candidate.candidate_version,
        )
    finally:
        db.close()


def _create_deployment(
    client: TestClient,
    headers: dict[str, str],
    seed: SeededCandidate,
    *,
    threshold: float = 0.75,
    criteria: dict | None = None,
):
    payload = {
        "candidate_id": seed.candidate_id,
        "proof_id": seed.proof_id,
        "object_type": "sales_order",
        "agreement_threshold": threshold,
    }
    payload.update(criteria or {})
    response = client.post(
        "/v1/deployments/shadow",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _case_payload(*, idempotency_key: str = "shadow-case-1") -> dict:
    return {
        "case_id": "SO-SHADOW-MISMATCH",
        "idempotency_key": idempotency_key,
        "event_types": ["sales.quote.created", "sales.quote.reviewed"],
        "object_attributes": _fake_sales_order(
            object_key="shadow-mismatch",
            formula_valid=False,
        ).model_dump(mode="json"),
        "actual_outcome": {"observed_status": "blocked", "source": "staging_event"},
    }


def _canonical_document(*, case_id: str, formula_valid: bool = True) -> dict:
    order = _fake_sales_order(object_key=case_id, formula_valid=formula_valid)
    return {
        "ocel:objects": {
            case_id: {
                "ocel:type": "sales_order",
                "ocel:ovmap": order.model_dump(mode="json"),
            }
        },
        "ocel:events": {
            f"{case_id}-created": {
                "ocel:activity": "sales.quote.created",
                "ocel:timestamp": "2026-07-30T09:00:00Z",
                "ocel:omap": [case_id],
                "ocel:vmap": {
                    "correlation_id": f"corr-{case_id}",
                    "historical": False,
                    "synthetic": False,
                },
            },
            f"{case_id}-reviewed": {
                "ocel:activity": "sales.quote.reviewed",
                "ocel:timestamp": "2026-07-30T09:05:00Z",
                "ocel:omap": [case_id],
                "ocel:vmap": {
                    "correlation_id": f"corr-{case_id}",
                    "historical": False,
                    "synthetic": False,
                },
            },
        },
    }


def test_shadow_compares_active_and_candidate_without_execution(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "shadow-auth")
    init_db()
    tenant_id = f"shadow-compare-{uuid4().hex}"
    seed = _seed_shadow_eligible_candidate(
        tenant_id=tenant_id,
        remove_formula_guard=True,
    )
    headers = _identity(tenant_id)
    client = TestClient(app)

    db = SessionLocal()
    try:
        executions_before = db.query(ExecutionRun).count()
    finally:
        db.close()

    deployment = _create_deployment(client, headers, seed)
    assert deployment["status"] == "shadow"
    assert deployment["no_effects"] is True
    assert deployment["agreement_threshold"] == 0.75

    response = client.post(
        f"/v1/deployments/{deployment['id']}/cases",
        headers=headers,
        json=_case_payload(),
    )
    assert response.status_code == 201, response.text
    result = response.json()
    assert result["active_decision"]["status"] == "failed"
    assert result["candidate_decision"]["status"] == "passed"
    assert result["agreement"] is False
    assert {"status_changed", "decision_removed"}.issubset(
        result["difference_categories"]
    )
    assert result["actual_outcome"]["source"] == "staging_event"
    assert len(result["deterministic_hash"]) == 64
    review = client.post(
        f"/v1/deployments/{deployment['id']}/cases/{result['id']}/reviews",
        headers=headers,
        json={
            "label": "unsafe_candidate",
            "notes": "Candidate omitted the blocking decision.",
        },
    )
    assert review.status_code == 201
    assert review.json()["label"] == "unsafe_candidate"

    db = SessionLocal()
    try:
        assert db.query(ExecutionRun).count() == executions_before
    finally:
        db.close()


def test_shadow_case_is_idempotent_and_conflicts_on_changed_input(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "shadow-auth")
    init_db()
    tenant_id = f"shadow-idempotent-{uuid4().hex}"
    seed = _seed_shadow_eligible_candidate(tenant_id=tenant_id)
    headers = _identity(tenant_id)
    client = TestClient(app)
    deployment = _create_deployment(client, headers, seed)
    url = f"/v1/deployments/{deployment['id']}/cases"

    first = client.post(url, headers=headers, json=_case_payload())
    repeated = client.post(url, headers=headers, json=_case_payload())
    assert first.status_code == repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    assert repeated.json()["deterministic_hash"] == first.json()["deterministic_hash"]

    changed = _case_payload()
    changed["actual_outcome"] = {"observed_status": "confirmed"}
    conflict = client.post(url, headers=headers, json=changed)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "shadow_idempotency_conflict"


def test_shadow_review_dashboard_and_tenant_isolation(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "shadow-auth")
    init_db()
    tenant_id = f"shadow-dashboard-{uuid4().hex}"
    seed = _seed_shadow_eligible_candidate(tenant_id=tenant_id)
    headers = _identity(tenant_id)
    client = TestClient(app)
    deployment = _create_deployment(
        client,
        headers,
        seed,
        threshold=0.95,
    )
    case = client.post(
        f"/v1/deployments/{deployment['id']}/cases",
        headers=headers,
        json=_case_payload(),
    ).json()
    review = client.post(
        f"/v1/deployments/{deployment['id']}/cases/{case['id']}/reviews",
        headers=headers,
        json={"label": "equivalent", "notes": "Same governed outcome."},
    )
    assert review.status_code == 201, review.text

    dashboard = client.get(
        f"/v1/deployments/{deployment['id']}/dashboard",
        headers=headers,
    )
    assert dashboard.status_code == 200
    metrics = dashboard.json()
    assert metrics["deployment_id"] == deployment["id"]
    assert metrics["status"] == "shadow"
    assert metrics["no_effects"] is True
    assert metrics["evaluated_case_count"] == 1
    assert metrics["agreement_rate"] == 1.0
    assert metrics["agreement_threshold"] == 0.95
    assert metrics["review_label_counts"] == {"equivalent": 1}
    assert metrics["operational_case_count"] == 0
    assert metrics["recommendation"] == "continue_shadow"
    assert metrics["recommendation_is_advisory"] is True
    cases = client.get(
        f"/v1/deployments/{deployment['id']}/cases",
        headers=headers,
    ).json()
    assert cases[0]["reviewer_label"] == "equivalent"
    assert len(cases[0]["reviews"]) == 1

    other_headers = _identity(f"other-{uuid4().hex}")
    isolated = client.get(
        f"/v1/deployments/{deployment['id']}",
        headers=other_headers,
    )
    assert isolated.status_code == 404


def test_shadow_rejects_proof_below_eligibility(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "shadow-auth")
    init_db()
    tenant_id = f"shadow-proof-{uuid4().hex}"
    seed = _seed_shadow_eligible_candidate(
        tenant_id=tenant_id,
        recommendation="needs_review",
    )
    response = TestClient(app).post(
        "/v1/deployments/shadow",
        headers=_identity(tenant_id),
        json={
            "candidate_id": seed.candidate_id,
            "proof_id": seed.proof_id,
            "object_type": "sales_order",
        },
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "proof_not_eligible_for_shadow"


def test_shadow_evidence_is_append_only():
    init_db()
    tenant_id = f"shadow-immutable-{uuid4().hex}"
    seed = _seed_shadow_eligible_candidate(tenant_id=tenant_id)
    db = SessionLocal()
    try:
        row = ShadowDeployment(
            id=f"shadow_{uuid4().hex}",
            tenant_id=tenant_id,
            candidate_id=seed.candidate_id,
            proof_id=seed.proof_id,
            process_key=seed.process_key,
            active_version=seed.base_version,
            candidate_version=seed.candidate_version,
            object_type="sales_order",
            status="shadow",
            agreement_threshold=0.9,
            no_effects=True,
            created_by="immutable-test",
        )
        db.add(row)
        db.commit()
        row.status = "promoted"
        with pytest.raises(ValueError, match="shadow_evidence_immutable"):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_shadow_service_has_no_connector_or_execution_dependency():
    source_path = ROOT / "erpguard" / "domain" / "shadow" / "service.py"
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    imports.update(
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    )
    assert not any(
        forbidden in imported
        for imported in imports
        for forbidden in ("connector", "execution", "permit", "odoo")
    )


def test_shadow_case_result_model_is_immutable():
    init_db()
    db = SessionLocal()
    try:
        row = ShadowCaseResult(
            id=f"shadowcase_{uuid4().hex}",
            tenant_id=f"shadow-result-{uuid4().hex}",
            deployment_id="shadow-test",
            case_id="case-test",
            idempotency_key="case-test",
            input_hash="input-hash",
            active_decision_json="{}",
            candidate_decision_json="{}",
            agreement=True,
            difference_categories_json="[]",
            deterministic_hash="result-hash",
        )
        db.add(row)
        db.commit()
        row.agreement = False
        with pytest.raises(ValueError, match="shadow_evidence_immutable"):
            db.commit()
    finally:
        db.rollback()
        db.close()


def test_canonical_ingestion_automatically_feeds_shadow_with_real_trace(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "shadow-auth")
    init_db()
    tenant_id = f"shadow-feed-{uuid4().hex}"
    seed = _seed_shadow_eligible_candidate(tenant_id=tenant_id)
    headers = _identity(tenant_id)
    client = TestClient(app)
    deployment = _create_deployment(client, headers, seed)
    case_id = f"so-operational-{uuid4().hex}"

    db = SessionLocal()
    try:
        executions_before = db.query(ExecutionRun).count()
    finally:
        db.close()
    imported = client.post(
        "/v1/events/ocel/import",
        headers=headers,
        json={
            "document": _canonical_document(case_id=case_id),
            "source": "odoo-bridge",
        },
    )
    assert imported.status_code == 201, imported.text
    assert imported.json()["shadow_deployments"] == 1
    assert imported.json()["shadow_evaluations"] == 1
    assert imported.json()["shadow_failures"] == 0

    cases = client.get(
        f"/v1/deployments/{deployment['id']}/cases",
        headers=headers,
    ).json()
    assert len(cases) == 1
    result = cases[0]
    assert result["case_id"] == case_id
    assert result["evaluation_mode"] == "canonical_feed"
    assert result["event_count"] == 2
    assert result["first_event_at"] == "2026-07-30T09:00:00Z"
    assert result["last_event_at"] == "2026-07-30T09:05:00Z"
    assert result["canonical_trace_hash"]
    assert result["trace_provenance"]["extraction_mode"] == "canonical_event_store"
    events = result["trace_provenance"]["events"]
    assert [event["source"] for event in events] == ["odoo-bridge", "odoo-bridge"]
    assert events[0]["correlation_id"] == f"corr-{case_id}"
    assert events[0]["object_links"]
    assert result["actual_outcome"] is None

    duplicate = client.post(
        "/v1/events/ocel/import",
        headers=headers,
        json={
            "document": _canonical_document(case_id=case_id),
            "source": "odoo-bridge",
        },
    )
    assert duplicate.status_code == 201
    assert duplicate.json()["shadow_evaluations"] == 0
    assert duplicate.json()["shadow_deduplications"] == 1
    assert len(
        client.get(
            f"/v1/deployments/{deployment['id']}/cases",
            headers=headers,
        ).json()
    ) == 1

    extended = {
        "ocel:objects": {
            case_id: {
                "ocel:type": "sales_order",
                "ocel:ovmap": _fake_sales_order(
                    object_key=case_id,
                    formula_valid=True,
                ).model_dump(mode="json"),
            }
        },
        "ocel:events": {
            f"{case_id}-ordered": {
                "ocel:activity": "sales.order.created",
                "ocel:timestamp": "2026-07-30T09:10:00Z",
                "ocel:omap": [case_id],
                "ocel:vmap": {
                    "correlation_id": f"corr-{case_id}",
                    "historical": False,
                    "synthetic": False,
                },
            }
        },
    }
    evolved = client.post(
        "/v1/events/ocel/import",
        headers=headers,
        json={"document": extended, "source": "odoo-bridge"},
    )
    assert evolved.status_code == 201
    assert evolved.json()["shadow_evaluations"] == 1
    evolved_cases = client.get(
        f"/v1/deployments/{deployment['id']}/cases",
        headers=headers,
    ).json()
    assert len(evolved_cases) == 2
    assert evolved_cases[0]["canonical_trace_hash"] != evolved_cases[1]["canonical_trace_hash"]
    assert evolved_cases[1]["event_count"] == 3

    explicit_feed = client.post(
        f"/v1/deployments/{deployment['id']}/feed/process",
        headers=headers,
        json={"case_ids": [case_id]},
    )
    assert explicit_feed.status_code == 201
    assert explicit_feed.json()["evaluated_case_count"] == 0
    assert explicit_feed.json()["deduplicated_case_count"] == 1
    dashboard = client.get(
        f"/v1/deployments/{deployment['id']}/dashboard",
        headers=headers,
    ).json()
    assert dashboard["evaluated_case_count"] == 1
    assert dashboard["operational_case_count"] == 1

    db = SessionLocal()
    try:
        assert db.query(ExecutionRun).count() == executions_before
        assert db.query(ShadowFeedRun).count() >= 2
    finally:
        db.close()


def test_outcome_reconciliation_is_deferred_provenanced_and_idempotent(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "shadow-auth")
    init_db()
    tenant_id = f"shadow-outcome-{uuid4().hex}"
    seed = _seed_shadow_eligible_candidate(tenant_id=tenant_id)
    headers = _identity(tenant_id)
    client = TestClient(app)
    deployment = _create_deployment(client, headers, seed)
    case_id = f"so-outcome-{uuid4().hex}"
    client.post(
        "/v1/events/ocel/import",
        headers=headers,
        json={
            "document": _canonical_document(case_id=case_id),
            "source": "odoo-bridge",
        },
    )
    result = client.get(
        f"/v1/deployments/{deployment['id']}/cases",
        headers=headers,
    ).json()[0]
    source_event_id = result["trace_provenance"]["events"][-1]["event_id"]
    payload = {
        "idempotency_key": "outcome-1",
        "outcome": {"state": "reviewed", "formula_valid": True},
        "observed_decision_status": "passed",
        "provenance": "odoo",
        "source_event_ids": [source_event_id],
        "observed_at": "2026-07-30T10:00:00Z",
    }
    url = f"/v1/deployments/{deployment['id']}/cases/{result['id']}/outcomes"
    first = client.post(url, headers=headers, json=payload)
    repeated = client.post(url, headers=headers, json=payload)
    assert first.status_code == repeated.status_code == 201
    assert repeated.json()["id"] == first.json()["id"]
    assert first.json()["provenance"] == "odoo"

    changed = {**payload, "outcome": {"state": "confirmed"}}
    conflict = client.post(url, headers=headers, json=changed)
    assert conflict.status_code == 409
    assert conflict.json()["detail"] == "shadow_outcome_idempotency_conflict"

    refreshed = client.get(
        f"/v1/deployments/{deployment['id']}/cases",
        headers=headers,
    ).json()[0]
    assert refreshed["actual_outcome"] == payload["outcome"]
    assert refreshed["actual_outcome_provenance"] == "odoo"
    assert len(refreshed["outcome_observations"]) == 1

    other_case_id = f"so-unrelated-{uuid4().hex}"
    client.post(
        "/v1/events/ocel/import",
        headers=headers,
        json={
            "document": _canonical_document(case_id=other_case_id),
            "source": "odoo-bridge",
        },
    )
    unrelated = next(
        item
        for item in client.get(
            f"/v1/deployments/{deployment['id']}/cases",
            headers=headers,
        ).json()
        if item["case_id"] == other_case_id
    )
    unrelated_event_id = unrelated["trace_provenance"]["events"][0]["event_id"]
    wrong_case_source = client.post(
        url,
        headers=headers,
        json={
            **payload,
            "idempotency_key": "outcome-wrong-case",
            "source_event_ids": [unrelated_event_id],
        },
    )
    assert wrong_case_source.status_code == 409
    assert wrong_case_source.json()["detail"] == "outcome_source_event_not_found"


def test_canary_eligibility_is_metrics_based_and_advisory_only(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "shadow-auth")
    init_db()
    tenant_id = f"shadow-metrics-{uuid4().hex}"
    seed = _seed_shadow_eligible_candidate(tenant_id=tenant_id)
    headers = _identity(tenant_id)
    client = TestClient(app)
    deployment = _create_deployment(
        client,
        headers,
        seed,
        threshold=0.9,
        criteria={
            "minimum_case_count": 1,
            "minimum_decision_coverage": 1.0,
            "minimum_review_coverage": 1.0,
            "minimum_outcome_reconciliation": 1.0,
            "observation_window_hours": 0,
        },
    )
    case_id = f"so-metrics-{uuid4().hex}"
    client.post(
        "/v1/events/ocel/import",
        headers=headers,
        json={
            "document": _canonical_document(case_id=case_id),
            "source": "odoo-bridge",
        },
    )
    result = client.get(
        f"/v1/deployments/{deployment['id']}/cases",
        headers=headers,
    ).json()[0]
    review_url = f"/v1/deployments/{deployment['id']}/cases/{result['id']}/reviews"
    assert client.post(
        review_url,
        headers=headers,
        json={"label": "equivalent", "notes": "Observed result agrees."},
    ).status_code == 201
    assert client.post(
        f"/v1/deployments/{deployment['id']}/cases/{result['id']}/outcomes",
        headers=headers,
        json={
            "idempotency_key": "metrics-outcome",
            "outcome": {"formula_valid": True},
            "observed_decision_status": "passed",
            "provenance": "odoo",
            "source_event_ids": [],
            "observed_at": "2026-07-30T10:00:00Z",
        },
    ).status_code == 201

    dashboard = client.get(
        f"/v1/deployments/{deployment['id']}/dashboard",
        headers=headers,
    ).json()
    assert dashboard["canonical_case_count"] == 1
    assert dashboard["case_coverage_rate"] == 1.0
    assert dashboard["decision_coverage_rate"] == 1.0
    assert dashboard["review_coverage_rate"] == 1.0
    assert dashboard["outcome_reconciliation_rate"] == 1.0
    assert dashboard["outcome_accuracy"] == 1.0
    assert dashboard["agreement_confidence_interval_95"]
    assert dashboard["outcome_accuracy_confidence_interval_95"]
    assert dashboard["recommendation"] == "eligible_for_canary"
    assert dashboard["recommendation_is_advisory"] is True
    assert all(dashboard["canary_eligibility_checks"].values())
    assert deployment["status"] == "shadow"

    assert client.post(
        review_url,
        headers=headers,
        json={"label": "unsafe_candidate", "notes": "Unresolved safety concern."},
    ).status_code == 201
    blocked = client.get(
        f"/v1/deployments/{deployment['id']}/dashboard",
        headers=headers,
    ).json()
    assert blocked["canary_eligibility_checks"]["no_unresolved_unsafe_candidate"] is False
    assert blocked["recommendation"] == "continue_shadow"


def test_outcome_and_feed_evidence_are_immutable():
    init_db()
    db = SessionLocal()
    try:
        outcome = ShadowOutcomeObservation(
            id=f"shadowoutcome_{uuid4().hex}",
            tenant_id=f"shadow-outcome-{uuid4().hex}",
            deployment_id="shadow-test",
            shadow_case_result_id="shadowcase-test",
            idempotency_key="outcome-test",
            outcome_json="{}",
            provenance="fixture",
            source_event_ids_json="[]",
            observed_at=datetime.now(timezone.utc),
            recorded_by="test",
            deterministic_hash="outcome-hash",
        )
        db.add(outcome)
        db.commit()
        outcome.provenance = "manual"
        with pytest.raises(ValueError, match="shadow_evidence_immutable"):
            db.commit()
    finally:
        db.rollback()
        db.close()
