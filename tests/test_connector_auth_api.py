from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_connector_auth_api_full_redacted_lifecycle():
    secret = "api_secret_never_return"
    response = client.post(
        "/v1/connectors/auth-profiles",
        json={
            "connector_id": "gmail",
            "display_name": "Gmail placeholder auth",
            "auth_type": "oauth_placeholder",
            "requested_scopes": ["gmail.readonly"],
            "credential": {"access_token": secret, "refresh_token": "refresh_never_return"},
            "created_by": {"type": "user", "id": "operator_1"},
        },
    )

    assert response.status_code == 200
    assert secret not in response.text
    assert "refresh_never_return" not in response.text
    body = response.json()
    profile_id = body["profile_id"]
    assert body["credential_ref"].startswith("vault_ref_")
    assert body["secret_redacted"] is True
    assert body["oauth_flow_enabled"] is False
    assert body["provider_api_calls_enabled"] is False

    detail = client.get(f"/v1/connectors/auth-profiles/{profile_id}")
    assert detail.status_code == 200
    assert secret not in detail.text

    listing = client.get("/v1/connectors/auth-profiles")
    assert listing.status_code == 200
    assert any(item["profile_id"] == profile_id for item in listing.json()["profiles"])
    assert secret not in listing.text

    simulated = client.post(f"/v1/connectors/auth-profiles/{profile_id}/test", json={"actor": {"id": "operator_1"}})
    assert simulated.status_code == 200
    assert simulated.json()["test_status"] == "simulated_passed"
    assert simulated.json()["provider_api_called"] is False
    assert simulated.json()["real_oauth_performed"] is False
    assert secret not in simulated.text

    rotated = client.post(
        f"/v1/connectors/auth-profiles/{profile_id}/rotate",
        json={"credential": {"access_token": "rotated_never_return"}, "actor": {"id": "operator_1"}},
    )
    assert rotated.status_code == 200
    assert rotated.json()["status"] == "rotated"
    assert "rotated_never_return" not in rotated.text

    revoked = client.post(f"/v1/connectors/auth-profiles/{profile_id}/revoke", json={"actor": {"id": "operator_1"}})
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"

    audit = client.get(f"/v1/connectors/auth-profiles/{profile_id}/audit")
    assert audit.status_code == 200
    assert [event["event_type"] for event in audit.json()["events"]] == [
        "profile_created",
        "simulated_connection_test",
        "credential_rotated",
        "credential_revoked",
    ]
    assert secret not in audit.text
    assert "rotated_never_return" not in audit.text


def test_connector_auth_scopes_endpoint_is_placeholder_only():
    response = client.get("/v1/connectors/scopes")

    assert response.status_code == 200
    body = response.json()
    connectors = {item["connector_id"]: item for item in body["scopes"]}
    assert connectors["google_calendar"]["oauth_flow_enabled"] is False
    assert connectors["google_calendar"]["provider_api_calls_enabled"] is False
    assert "calendar.readonly" in connectors["google_calendar"]["available_scopes"]


def test_connector_auth_missing_profile_returns_controlled_error():
    response = client.get("/v1/connectors/auth-profiles/auth_profile_missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "auth_profile_not_found"
