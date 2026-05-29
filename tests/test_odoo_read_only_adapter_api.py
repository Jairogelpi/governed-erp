"""Tests for Sprint 74 - Odoo read-only adapter shell API."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _activation():
    session = client.post(
        "/v1/operator-console/connectors/setup-session",
        json={
            "connector_name": "odoo_adapter_api",
            "erp_url": "https://adapter-api.odoo.com",
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
            "password": "api-odoo-ro-secret",
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
    capability_set = client.post(
        "/v1/operator-console/connectors/safe-discovery-plan/"
        f"{discovery['discovery_plan_id']}/generated-capabilities",
        json={"created_by": "operator_1"},
    ).json()
    request = client.post(
        "/v1/operator-console/connectors/generated-capabilities/"
        f"{capability_set['capability_set_id']}/read-only-activation-request",
        json={"requested_by": "operator_1", "mode": "read_only"},
    ).json()
    return client.post(
        "/v1/operator-console/connectors/read-only-activation/"
        f"{request['activation_request_id']}/approve",
        json={"approved_by": "operator_1"},
    ).json()


def test_api_creates_retrieves_and_lists_adapter_session():
    activation = _activation()

    create_resp = client.post(
        "/v1/operator-console/connectors/read-only-activation/"
        f"{activation['activation_id']}/odoo-adapter-session",
        json={"created_by": "operator_1"},
    )

    assert create_resp.status_code == 200
    created = create_resp.json()
    assert created["adapter_session_id"].startswith("odoo_ro_")
    assert created["status"] == "prepared"
    assert created["can_connect_later"] is True
    assert created["will_connect_now"] is False
    assert created["external_http_performed"] is False
    assert created["login_attempted"] is False
    assert created["odoo_rpc_performed"] is False
    assert created["odoo_read_performed"] is False
    assert created["odoo_write_performed"] is False
    assert created["raw_secret_accessed"] is False

    get_resp = client.get(
        "/v1/operator-console/connectors/odoo-adapter-session/"
        f"{created['adapter_session_id']}"
    )
    assert get_resp.status_code == 200
    assert get_resp.json()["adapter_session_id"] == created["adapter_session_id"]

    list_resp = client.get("/v1/operator-console/connectors/odoo-adapter-sessions")
    assert list_resp.status_code == 200
    assert any(
        item["adapter_session_id"] == created["adapter_session_id"]
        for item in list_resp.json()["sessions"]
    )


def test_api_blocks_missing_activation():
    resp = client.post(
        "/v1/operator-console/connectors/read-only-activation/roconn_missing/odoo-adapter-session",
        json={"created_by": "operator_1"},
    )

    assert resp.status_code == 200
    assert resp.json()["status"] == "blocked"
    assert "activation_not_found" in resp.json()["blocking_reasons"]


def test_api_returns_odoo_adapter_audit():
    activation = _activation()
    client.post(
        "/v1/operator-console/connectors/read-only-activation/"
        f"{activation['activation_id']}/odoo-adapter-session",
        json={"created_by": "operator_1"},
    )

    resp = client.get("/v1/operator-console/connectors/odoo-adapter-audit")

    assert resp.status_code == 200
    events = resp.json()["events"]
    assert any(e["event_type"] == "odoo_read_only_adapter_session_created" for e in events)
    assert "api-odoo-ro-secret" not in str(events)
