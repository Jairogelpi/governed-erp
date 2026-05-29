"""Tests for Sprint 58 - generated capabilities API."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _create_safe_discovery_plan():
    session_resp = client.post(
        "/v1/operator-console/connectors/setup-session",
        json={
            "connector_name": "odoo_generated_api",
            "erp_url": "https://generated-api.odoo.com",
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
            "password": "api-generated-secret",
            "submitted_by": "operator_1",
        },
    )
    credential_ref = seal_resp.json()["credential_ref"]
    fp_resp = client.post(
        f"/v1/operator-console/connectors/setup-session/{session_id}/fingerprinting-plan",
        json={
            "setup_session_id": session_id,
            "credential_ref": credential_ref,
            "created_by": "operator_1",
        },
    )
    discovery_resp = client.post(
        "/v1/operator-console/connectors/fingerprinting-plan/"
        f"{fp_resp.json()['fingerprint_plan_id']}/safe-discovery-plan",
        json={"created_by": "operator_1"},
    )
    return discovery_resp.json()


def test_api_generates_retrieves_and_lists_capability_set():
    discovery = _create_safe_discovery_plan()

    create_resp = client.post(
        "/v1/operator-console/connectors/safe-discovery-plan/"
        f"{discovery['discovery_plan_id']}/generated-capabilities",
        json={"created_by": "operator_1"},
    )

    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["capability_set_id"].startswith("gcaps_")
    assert created["status"] == "generated"
    assert created["adapter_id"].startswith("generated_odoo_")
    assert created["capabilities"]
    assert created["blocked_capabilities"]
    assert created["is_advisory_only"] is True
    assert created["will_execute"] is False
    assert created["can_execute"] is False
    assert created["external_http_performed"] is False
    assert created["login_attempted"] is False
    assert created["schema_inspection_performed"] is False
    assert created["permission_inspection_performed"] is False
    assert created["sample_data_read"] is False
    assert created["read_only_activation_performed"] is False
    assert created["erp_write_performed"] is False
    assert created["credentials_exposed"] is False
    assert created["raw_secret_accessed"] is False

    get_resp = client.get(
        "/v1/operator-console/connectors/generated-capabilities/"
        f"{created['capability_set_id']}"
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["capability_set_id"] == created["capability_set_id"]

    list_resp = client.get("/v1/operator-console/connectors/generated-capability-sets")
    assert list_resp.status_code == 200
    assert any(
        item["capability_set_id"] == created["capability_set_id"]
        for item in list_resp.json()["capability_sets"]
    )


def test_api_blocks_missing_safe_discovery_plan():
    resp = client.post(
        "/v1/operator-console/connectors/safe-discovery-plan/dplan_missing/generated-capabilities",
        json={"created_by": "operator_1"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert "safe_discovery_plan_not_found" in data["blocking_reasons"]


def test_api_generated_capability_audit():
    discovery = _create_safe_discovery_plan()
    client.post(
        "/v1/operator-console/connectors/safe-discovery-plan/"
        f"{discovery['discovery_plan_id']}/generated-capabilities",
        json={"created_by": "operator_1"},
    )

    resp = client.get("/v1/operator-console/connectors/generated-capability-audit")

    assert resp.status_code == 200
    events = resp.json()["events"]
    assert any(e["event_type"] == "generated_capabilities_created" for e in events)
    assert "api-generated-secret" not in str(events)
