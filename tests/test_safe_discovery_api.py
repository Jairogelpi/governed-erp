"""Tests for Sprint 57 - Safe Discovery Plan API."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _create_fingerprinting_plan(connector_name="odoo_api", host="api.odoo.com"):
    session_resp = client.post(
        "/v1/operator-console/connectors/setup-session",
        json={
            "connector_name": connector_name,
            "erp_url": f"https://{host}",
            "environment_type": "production",
            "submitted_by": "operator_1",
        },
    )
    session_id = session_resp.json()["session_id"]
    seal_resp = client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": session_id,
            "auth_type": "password",
            "username": "admin@example.com",
            "password": "api-secret",
            "submitted_by": "operator_1",
        },
    )
    cred_ref = seal_resp.json()["credential_ref"]
    fp_resp = client.post(
        f"/v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan",
        json={
            "setup_session_id": session_id,
            "credential_ref": cred_ref,
            "created_by": "operator_1",
        },
    )
    return fp_resp.json(), cred_ref


def test_api_creates_retrieves_and_lists_safe_discovery_plan():
    fingerprint, _ = _create_fingerprinting_plan()

    create_resp = client.post(
        "/v1/operator-console/connectors/fingerprinting-plan/"
        f"{fingerprint['fingerprint_plan_id']}/safe-discovery-plan",
        json={"created_by": "operator_1"},
    )

    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["discovery_plan_id"].startswith("dplan_")
    assert created["status"] == "planned"
    assert created["selected_adapter_type"] == "odoo"
    assert created["will_connect"] is False
    assert created["external_http_performed"] is False
    assert created["login_attempted"] is False
    assert created["schema_inspection_performed"] is False
    assert created["permission_inspection_performed"] is False
    assert created["sample_data_read"] is False
    assert created["capability_generation_performed"] is False
    assert created["read_only_activation_performed"] is False
    assert created["erp_write_performed"] is False
    assert created["credentials_exposed"] is False
    assert created["raw_secret_accessed"] is False

    get_resp = client.get(
        "/v1/operator-console/connectors/safe-discovery-plan/"
        f"{created['discovery_plan_id']}"
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["discovery_plan_id"] == created["discovery_plan_id"]

    list_resp = client.get("/v1/operator-console/connectors/safe-discovery-plans")
    assert list_resp.status_code == 200
    assert any(
        item["discovery_plan_id"] == created["discovery_plan_id"]
        for item in list_resp.json()["plans"]
    )


def test_api_blocks_missing_fingerprinting_plan():
    resp = client.post(
        "/v1/operator-console/connectors/fingerprinting-plan/fplan_missing/safe-discovery-plan",
        json={"created_by": "operator_1"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert "fingerprinting_plan_not_found" in data["blocking_reasons"]


def test_api_accepts_explicit_candidate_adapter():
    fingerprint, _ = _create_fingerprinting_plan(
        connector_name="custom_api", host="custom.example.com"
    )

    resp = client.post(
        "/v1/operator-console/connectors/fingerprinting-plan/"
        f"{fingerprint['fingerprint_plan_id']}/safe-discovery-plan",
        json={"selected_adapter_type": "custom_rest", "created_by": "operator_1"},
    )

    assert resp.status_code == 200
    assert resp.json()["selected_adapter_type"] == "custom_rest"


def test_api_audit_endpoint_records_created_event_and_no_raw_secret():
    fingerprint, _ = _create_fingerprinting_plan()
    client.post(
        "/v1/operator-console/connectors/fingerprinting-plan/"
        f"{fingerprint['fingerprint_plan_id']}/safe-discovery-plan",
        json={"created_by": "operator_1"},
    )

    resp = client.get("/v1/operator-console/connectors/safe-discovery-audit")

    assert resp.status_code == 200
    events = resp.json()["events"]
    assert any(e["event_type"] == "safe_discovery_plan_created" for e in events)
    assert "api-secret" not in str(events)
