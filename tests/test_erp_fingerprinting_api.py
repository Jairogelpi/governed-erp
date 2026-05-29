"""Tests for Sprint 56 — ERP Fingerprinting Plan API endpoints."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _create_session_and_seal():
    # Create a setup session
    session_resp = client.post(
        "/v1/operator-console/connectors/setup-session",
        json={
            "connector_name": "odoo_test_fp",
            "erp_url": "https://demo.odoo.com",
            "environment_type": "production",
            "submitted_by": "operator_1",
        },
    )
    session_id = session_resp.json()["session_id"]

    # Seal a credential
    seal_resp = client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": session_id,
            "auth_type": "password",
            "username": "admin@example.com",
            "password": "test-password",
            "submitted_by": "operator_1",
        },
    )
    cred_ref = seal_resp.json()["credential_ref"]
    return session_id, cred_ref


def test_create_fingerprinting_plan():
    session_id, cred_ref = _create_session_and_seal()

    resp = client.post(
        f"/v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan",
        json={
            "setup_session_id": session_id,
            "credential_ref": cred_ref,
            "created_by": "operator_1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["fingerprint_plan_id"].startswith("fplan_")
    assert data["status"] == "planned"
    assert data["will_connect"] is False
    assert data["external_http_performed"] is False
    assert data["login_attempted"] is False
    assert data["fingerprint_performed"] is False
    assert data["schema_inspection_performed"] is False
    assert data["capability_generation_performed"] is False
    assert data["read_only_activation_performed"] is False
    assert data["credentials_exposed"] is False
    assert data["raw_secret_accessed"] is False


def test_create_plan_with_manual_hint():
    session_id, cred_ref = _create_session_and_seal()

    resp = client.post(
        f"/v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan",
        json={
            "setup_session_id": session_id,
            "credential_ref": cred_ref,
            "created_by": "operator_1",
            "manual_hint": "odoo",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "planned"
    adapter_types = [c["adapter_type"] for c in data["adapter_candidates"]]
    assert "odoo" in adapter_types


def test_blocks_missing_session():
    resp = client.post(
        "/v1/operator-console/connectors/setup-session/csess_nonexistent/fingerprinting-plan",
        json={
            "setup_session_id": "csess_nonexistent",
            "credential_ref": "cred_test",
            "created_by": "operator_1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert "setup_session_not_found" in data["blocking_reasons"]


def test_get_fingerprinting_plan():
    session_id, cred_ref = _create_session_and_seal()

    create_resp = client.post(
        f"/v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan",
        json={
            "setup_session_id": session_id,
            "credential_ref": cred_ref,
            "created_by": "operator_1",
        },
    )
    plan_id = create_resp.json()["fingerprint_plan_id"]

    resp = client.get(f"/v1/operator-console/connectors/fingerprinting-plan/{plan_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["fingerprint_plan_id"] == plan_id
    assert data["status"] == "planned"


def test_get_plan_not_found():
    resp = client.get(
        "/v1/operator-console/connectors/fingerprinting-plan/fplan_nonexistent"
    )
    assert resp.status_code == 404


def test_list_fingerprinting_plans():
    session_id, cred_ref = _create_session_and_seal()

    client.post(
        f"/v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan",
        json={
            "setup_session_id": session_id,
            "credential_ref": cred_ref,
            "created_by": "operator_1",
        },
    )

    resp = client.get("/v1/operator-console/connectors/fingerprinting-plans")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["plans"]) >= 1


def test_fingerprinting_audit():
    session_id, cred_ref = _create_session_and_seal()

    client.post(
        f"/v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan",
        json={
            "setup_session_id": session_id,
            "credential_ref": cred_ref,
            "created_by": "operator_1",
        },
    )

    resp = client.get("/v1/operator-console/connectors/fingerprinting-audit")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) >= 1
    event = data["events"][0]
    assert event["event_type"] == "fingerprinting_plan_created"


def test_audit_does_not_contain_raw_secrets():
    session_id, cred_ref = _create_session_and_seal()

    client.post(
        f"/v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan",
        json={
            "setup_session_id": session_id,
            "credential_ref": cred_ref,
            "created_by": "operator_1",
        },
    )

    resp = client.get("/v1/operator-console/connectors/fingerprinting-audit")
    data = resp.json()
    for event in data["events"]:
        assert "test-password" not in str(event)
