from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)
BASE = "/v1/operator-console/connectors"


def _payload(**overrides):
    payload = {
        "connector_name": "Odoo Production",
        "erp_url": "https://miempresa.odoo.com/web/login",
        "environment_type": "production",
        "submitted_by": "operator_1",
    }
    payload.update(overrides)
    return payload


def test_api_creates_session_and_normalizes_host():
    response = client.post(f"{BASE}/setup-session", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"].startswith("csess_")
    assert body["erp_url_host"] == "miempresa.odoo.com"
    assert body["status"] == "awaiting_credentials"
    assert body["credential_mode"] == "not_provided"
    assert body["requires_credentials"] is True
    assert body["can_fingerprint"] is False
    assert body["can_activate_read_only"] is False
    assert body["will_connect"] is False
    assert body["external_http_performed"] is False
    assert body["credentials_stored"] is False
    assert body["raw_credentials_seen"] is False


def test_api_gets_created_session():
    created = client.post(f"{BASE}/setup-session", json=_payload(connector_name="Get Me")).json()

    response = client.get(f"{BASE}/setup-session/{created['session_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["session_id"] == created["session_id"]
    assert body["connector_name"] == "Get Me"
    assert body["will_connect"] is False


def test_api_lists_sessions_with_safety_flags():
    created = client.post(f"{BASE}/setup-session", json=_payload(connector_name="List Me")).json()

    response = client.get(f"{BASE}/setup-sessions")

    assert response.status_code == 200
    body = response.json()
    assert any(item["session_id"] == created["session_id"] for item in body["sessions"])
    assert body["will_connect"] is False
    assert body["external_http_performed"] is False
    assert body["credentials_stored"] is False


def test_api_invalid_url_returns_blocked_session():
    response = client.post(f"{BASE}/setup-session", json=_payload(erp_url="not-a-url"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert "invalid_erp_url" in body["blocking_reasons"]
    assert body["will_connect"] is False
    assert body["external_http_performed"] is False


def test_api_external_http_url_blocks_as_unsafe():
    response = client.post(f"{BASE}/setup-session", json=_payload(erp_url="http://erp.example.com"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["erp_url_host"] == "erp.example.com"
    assert "unsafe_url_scheme" in body["blocking_reasons"]
    assert body["login_attempted"] is False


def test_api_raw_credential_fields_are_blocked_and_not_echoed():
    response = client.post(
        f"{BASE}/setup-session",
        json=_payload(password="do_not_store_me", credentials={"api_key": "also_do_not_store"}),
    )

    assert response.status_code == 200
    assert "do_not_store_me" not in response.text
    assert "also_do_not_store" not in response.text
    body = response.json()
    assert body["status"] == "blocked"
    assert body["raw_credentials_seen"] is True
    assert "raw_credentials_not_allowed_in_sprint_54" in body["blocking_reasons"]
    assert body["credentials_stored"] is False


def test_api_accepts_opaque_credential_ref_without_storing_raw_credentials():
    response = client.post(f"{BASE}/setup-session", json=_payload(credential_ref="vault_ref_future_123"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready_for_fingerprint"
    assert body["credential_mode"] == "vault_reference_only"
    assert body["credential_ref"] == "vault_ref_future_123"
    assert body["credentials_stored"] is False
    assert body["fingerprint_performed"] is False
    assert body["can_fingerprint"] is False


def test_missing_session_returns_controlled_404():
    response = client.get(f"{BASE}/setup-session/csess_missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "connector_setup_session_not_found"
