"""Tests for Sprint 59 - Read-Only Connector Activation API."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _capability_set():
    session = client.post(
        "/v1/operator-console/connectors/setup-session",
        json={
            "connector_name": "odoo_ro_api",
            "erp_url": "https://readonly-api.odoo.com",
            "environment_type": "production",
            "submitted_by": "operator_1",
        },
    ).json()
    credential = client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": session["session_id"],
            "auth_type": "password",
            "username": "admin@example.com",
            "password": "api-ro-secret",
            "submitted_by": "operator_1",
        },
    ).json()
    fingerprint = client.post(
        f"/v1/operator-console/connectors/setup-session/{session['session_id']}/fingerprinting-plan",
        json={
            "setup_session_id": session["session_id"],
            "credential_ref": credential["credential_ref"],
            "created_by": "operator_1",
        },
    ).json()
    discovery = client.post(
        "/v1/operator-console/connectors/fingerprinting-plan/"
        f"{fingerprint['fingerprint_plan_id']}/safe-discovery-plan",
        json={"created_by": "operator_1"},
    ).json()
    return client.post(
        "/v1/operator-console/connectors/safe-discovery-plan/"
        f"{discovery['discovery_plan_id']}/generated-capabilities",
        json={"created_by": "operator_1"},
    ).json()


def test_api_creates_request_approves_retrieves_and_lists_activation():
    capability_set = _capability_set()

    request_resp = client.post(
        "/v1/operator-console/connectors/generated-capabilities/"
        f"{capability_set['capability_set_id']}/read-only-activation-request",
        json={"requested_by": "operator_1", "mode": "read_only"},
    )

    assert request_resp.status_code == 200
    request = request_resp.json()
    assert request["activation_request_id"].startswith("roactreq_")
    assert request["status"] == "requested"
    assert request["requires_human_approval"] is True
    assert request["will_connect"] is False
    assert request["can_read_real_erp"] is False
    assert request["can_write_real_erp"] is False

    approve_resp = client.post(
        "/v1/operator-console/connectors/read-only-activation/"
        f"{request['activation_request_id']}/approve",
        json={"approved_by": "operator_1"},
    )
    assert approve_resp.status_code == 200
    activation = approve_resp.json()
    assert activation["activation_id"].startswith("roconn_")
    assert activation["status"] == "active_read_only"
    assert activation["real_erp_connection_established"] is False
    assert activation["real_erp_read_enabled"] is False
    assert activation["real_erp_write_enabled"] is False
    assert activation["external_http_performed"] is False
    assert activation["login_attempted"] is False
    assert activation["credentials_exposed"] is False
    assert activation["raw_secret_accessed"] is False

    get_resp = client.get(
        "/v1/operator-console/connectors/read-only-activation/"
        f"{activation['activation_id']}"
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["activation_id"] == activation["activation_id"]

    list_resp = client.get("/v1/operator-console/connectors/read-only-activations")
    assert list_resp.status_code == 200
    assert any(
        item["activation_id"] == activation["activation_id"]
        for item in list_resp.json()["activations"]
    )


def test_api_blocks_missing_capability_set():
    resp = client.post(
        "/v1/operator-console/connectors/generated-capabilities/gcaps_missing/read-only-activation-request",
        json={"requested_by": "operator_1", "mode": "read_only"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "blocked"
    assert "capability_set_not_found" in resp.json()["blocking_reasons"]


def test_api_returns_activation_audit():
    capability_set = _capability_set()
    request = client.post(
        "/v1/operator-console/connectors/generated-capabilities/"
        f"{capability_set['capability_set_id']}/read-only-activation-request",
        json={"requested_by": "operator_1", "mode": "read_only"},
    ).json()
    client.post(
        "/v1/operator-console/connectors/read-only-activation/"
        f"{request['activation_request_id']}/approve",
        json={"approved_by": "operator_1"},
    )

    resp = client.get("/v1/operator-console/connectors/read-only-activation-audit")

    assert resp.status_code == 200
    events = resp.json()["events"]
    assert any(e["event_type"] == "read_only_activation_request_created" for e in events)
    assert any(e["event_type"] == "read_only_activation_approved" for e in events)
    assert any(e["event_type"] == "read_only_connector_activated" for e in events)
    assert "api-ro-secret" not in str(events)
