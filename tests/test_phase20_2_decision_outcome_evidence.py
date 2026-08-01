"""Spec 92 Workstream D -- decision-to-outcome evidence bundle (Sec 11, 18).

Reuses Phase 20.1's full A -> C chain (`_converted_recommendation` +
`_plan_and_approve` + capture-followup + evaluate) to reach a state where
every manifest resource genuinely exists, then drives the bundle endpoints.
"""

from __future__ import annotations

import json

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy import update

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.decision_outcome_evidence import DecisionOutcomeEvidenceBundle
from erpguard.db.session import SessionLocal, init_db

from test_phase14_skill_compiler import _identity
from test_phase20_1_realized_outcomes import _converted_recommendation, _plan_and_approve, _valid_observed


def _setup(monkeypatch) -> tuple[TestClient, dict, str]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    monkeypatch.setattr(settings, "allow_pricing_scenario_draft", True)
    init_db()
    tenant_id = f"evidence-tenant-{__import__('uuid').uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers, tenant_id


def _full_lifecycle(client, headers, monkeypatch, tenant_id) -> dict:
    """Drives A (recommendation->execution) then C (measurement->report) to
    completion. Returns the recommendation id."""

    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)
    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(gross_margin="500.00")},
    )
    evaluate_resp = client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)
    assert evaluate_resp.status_code == 200, evaluate_resp.text
    return recommendation_id


def test_complete_chain_seals(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    recommendation_id = _full_lifecycle(client, headers, monkeypatch, tenant_id)

    create_resp = client.post(
        f"/v1/recommendations/{recommendation_id}/evidence-bundle", headers=headers, json={}
    )
    assert create_resp.status_code == 201, create_resp.text
    bundle = create_resp.json()
    assert bundle["status"] == "sealed", bundle
    assert bundle["sealed_at"] is not None
    assert bundle["missing_resources"] == []

    resource_types = {item["resource_type"] for item in bundle["manifest"]}
    for required in (
        "analytical_snapshot", "data_quality_report", "margin_analysis", "margin_opportunity",
        "governed_recommendation", "recommendation_approval", "action_draft", "action_validation",
        "execution_run", "execution_approval", "execution_permit", "postcondition_result",
        "execution_evidence_pack", "measurement_plan", "outcome_observation", "realized_outcome_report",
    ):
        assert required in resource_types, f"missing {required} in sealed manifest"


def test_missing_resource_remains_incomplete(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    # No measurement plan / outcome report created -- Workstream C never ran.

    create_resp = client.post(
        f"/v1/recommendations/{recommendation_id}/evidence-bundle", headers=headers, json={}
    )
    assert create_resp.status_code == 201, create_resp.text
    bundle = create_resp.json()
    assert bundle["status"] == "incomplete"
    assert bundle["sealed_at"] is None
    assert "measurement_plan" in bundle["missing_resources"]
    assert "outcome_observation" in bundle["missing_resources"]
    assert "realized_outcome_report" in bundle["missing_resources"]


def test_another_tenant_cannot_read_bundle(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    recommendation_id = _full_lifecycle(client, headers, monkeypatch, tenant_id)
    bundle_id = client.post(
        f"/v1/recommendations/{recommendation_id}/evidence-bundle", headers=headers, json={}
    ).json()["id"]

    other_headers = _identity(f"other-tenant-{__import__('uuid').uuid4().hex}")
    resp = client.get(f"/v1/decision-outcome-evidence/{bundle_id}", headers=other_headers)
    assert resp.status_code == 404


def test_altered_stored_hash_fails_verification_and_read(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    recommendation_id = _full_lifecycle(client, headers, monkeypatch, tenant_id)
    bundle_id = client.post(
        f"/v1/recommendations/{recommendation_id}/evidence-bundle", headers=headers, json={}
    ).json()["id"]

    # Simulate a raw tamper (e.g. direct DB access) rather than an
    # application-level update -- the sealed-immutability event listener
    # blocks ORM-level mutation entirely, which is exactly the behavior
    # under test elsewhere; a Core-level UPDATE bypasses ORM mapper events,
    # the same way `test_phase15_execution_permit_runtime.py` simulates
    # tampering with an otherwise-immutable row.
    db = SessionLocal()
    try:
        row = db.query(DecisionOutcomeEvidenceBundle).filter_by(id=bundle_id).one()
        manifest = json.loads(row.manifest_json)
        manifest[0]["content_hash"] = "tampered"
        db.execute(
            update(DecisionOutcomeEvidenceBundle)
            .where(DecisionOutcomeEvidenceBundle.id == bundle_id)
            .values(manifest_json=json.dumps(manifest))
        )
        db.commit()
    finally:
        db.close()

    get_resp = client.get(f"/v1/decision-outcome-evidence/{bundle_id}", headers=headers)
    assert get_resp.status_code == 409
    assert "evidence_integrity_failed" in get_resp.json()["detail"]

    verify_resp = client.get(f"/v1/decision-outcome-evidence/{bundle_id}/verify", headers=headers)
    assert verify_resp.status_code == 200, verify_resp.text
    result = verify_resp.json()
    assert result["verified"] is False
    assert result["stored_hashes_intact"] is False


def test_secret_like_field_rejected_from_export(monkeypatch):
    from erpguard.domain.evidence.decision_outcome_bundle import contains_secret_like_field

    assert contains_secret_like_field({"api_key": "abc"}) is True
    assert contains_secret_like_field({"credential_ref": "cred_x"}) is True
    assert contains_secret_like_field([{"nested": {"password": "x"}}]) is True
    assert contains_secret_like_field({"customer_reference": "GERP-rec-1"}) is False


def test_sealed_bundle_is_immutable(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    recommendation_id = _full_lifecycle(client, headers, monkeypatch, tenant_id)
    bundle_id = client.post(
        f"/v1/recommendations/{recommendation_id}/evidence-bundle", headers=headers, json={}
    ).json()["id"]

    db = SessionLocal()
    try:
        row = db.query(DecisionOutcomeEvidenceBundle).filter_by(id=bundle_id).one()
        assert row.status == "sealed"
        row.status = "building"
        with pytest.raises(ValueError, match="decision_outcome_evidence_bundle_sealed_immutable"):
            db.commit()
        db.rollback()
    finally:
        db.close()


def test_exported_json_contains_reality_labels(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    recommendation_id = _full_lifecycle(client, headers, monkeypatch, tenant_id)
    bundle_resp = client.post(
        f"/v1/recommendations/{recommendation_id}/evidence-bundle", headers=headers, json={}
    )
    bundle = bundle_resp.json()
    assert bundle["manifest"], "manifest must not be empty"
    for item in bundle["manifest"]:
        assert item["reality_label"] in {"live", "staging_live", "fixture", "synthetic", "derived", "manual"}


def test_execution_and_outcome_evidence_are_linked(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    result = _converted_recommendation(client, headers, monkeypatch, tenant_id)
    recommendation_id = result["recommendation"]["id"]
    run_id = result["run_id"]
    plan = _plan_and_approve(client, headers, tenant_id, recommendation_id)
    client.post(
        f"/v1/measurement-plans/{plan['id']}/capture-followup", headers=headers,
        json={"observed": _valid_observed(gross_margin="500.00")},
    )
    client.post(f"/v1/measurement-plans/{plan['id']}/evaluate", headers=headers)

    bundle = client.post(
        f"/v1/recommendations/{recommendation_id}/evidence-bundle", headers=headers, json={}
    ).json()
    assert bundle["status"] == "sealed"

    by_type = {item["resource_type"]: item["resource_id"] for item in bundle["manifest"]}
    assert by_type["execution_run"] == run_id
    assert by_type["measurement_plan"] == plan["id"]


def test_no_secret_present_in_sealed_manifest(monkeypatch):
    client, headers, tenant_id = _setup(monkeypatch)
    recommendation_id = _full_lifecycle(client, headers, monkeypatch, tenant_id)
    bundle = client.post(
        f"/v1/recommendations/{recommendation_id}/evidence-bundle", headers=headers, json={}
    ).json()
    assert "secret" not in json.dumps(bundle).lower()
    assert "credential" not in json.dumps(bundle).lower()
