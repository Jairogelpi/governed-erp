from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

_PROFILE_ID = "api_oauth_test_profile_s19"
_ALLOWED_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"


def _create_profile(profile_id: str = _PROFILE_ID) -> str:
    r = client.post(
        "/v1/connectors/auth-profiles",
        json={
            "connector_id": "google_calendar_readonly",
            "display_name": "Sprint 19 OAuth Test",
            "auth_type": "oauth",
            "requested_scopes": [_ALLOWED_SCOPE],
            "credential": {},
            "created_by": {"id": "test_operator"},
        },
    )
    return r.json()["profile_id"]


def test_authorize_returns_url_and_state():
    profile_id = _create_profile("s19_authorize_profile")
    r = client.post(
        "/v1/oauth/google-calendar/authorize",
        json={"profile_id": profile_id, "actor": {"id": "test"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert "authorization_url" in body
    assert "state_token" in body
    assert body["token_exposed"] is False
    assert body["secret_redacted"] is True
    assert body["placeholder_mode"] is True
    assert _ALLOWED_SCOPE in body["authorization_url"]


def test_authorize_never_exposes_client_secret():
    profile_id = _create_profile("s19_secret_check_profile")
    r = client.post(
        "/v1/oauth/google-calendar/authorize",
        json={"profile_id": profile_id},
    )
    body_str = r.text
    assert "placeholder_client_secret" not in body_str
    assert "client_secret" not in body_str.lower().replace("secret_redacted", "")


def test_callback_placeholder_exchange():
    profile_id = _create_profile("s19_callback_profile")
    auth_r = client.post(
        "/v1/oauth/google-calendar/authorize",
        json={"profile_id": profile_id},
    )
    state_token = auth_r.json()["state_token"]

    r = client.get(f"/v1/oauth/google-calendar/callback?code=placeholder_code&state={state_token}")
    assert r.status_code == 200
    body = r.json()
    assert body["profile_id"] == profile_id
    assert body["token_exposed"] is False
    assert body["secret_redacted"] is True
    assert body["scope_compliant"] is True
    assert body["placeholder_mode"] is True
    assert "access_token" not in body
    assert "refresh_token" not in body


def test_callback_invalid_state_returns_400():
    r = client.get("/v1/oauth/google-calendar/callback?code=code&state=invalid_state_xyz_123")
    assert r.status_code == 400
    body = r.json()
    assert body["error"]["code"] == "invalid_state"


def test_callback_cannot_be_replayed():
    profile_id = _create_profile("s19_replay_profile")
    auth_r = client.post(
        "/v1/oauth/google-calendar/authorize",
        json={"profile_id": profile_id},
    )
    state_token = auth_r.json()["state_token"]
    client.get(f"/v1/oauth/google-calendar/callback?code=code&state={state_token}")
    # Second use of same state token must fail
    r2 = client.get(f"/v1/oauth/google-calendar/callback?code=code&state={state_token}")
    assert r2.status_code == 400


def test_get_auth_status_not_authorized():
    r = client.get("/v1/oauth/google-calendar/status/never_authorized_profile_s19")
    assert r.status_code == 200
    body = r.json()
    assert body["authorized"] is False
    assert body["token_exposed"] is False


def test_get_auth_status_after_exchange():
    profile_id = _create_profile("s19_status_after_exchange")
    auth_r = client.post("/v1/oauth/google-calendar/authorize", json={"profile_id": profile_id})
    state = auth_r.json()["state_token"]
    client.get(f"/v1/oauth/google-calendar/callback?code=code&state={state}")
    r = client.get(f"/v1/oauth/google-calendar/status/{profile_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["authorized"] is True
    assert body["scope_compliant"] is True
    assert body["token_exposed"] is False
    assert "access_token" not in body
    assert "refresh_token" not in body


def test_verify_scope_compliant():
    profile_id = _create_profile("s19_verify_scope_profile")
    auth_r = client.post("/v1/oauth/google-calendar/authorize", json={"profile_id": profile_id})
    state = auth_r.json()["state_token"]
    client.get(f"/v1/oauth/google-calendar/callback?code=code&state={state}")
    r = client.get(f"/v1/oauth/google-calendar/verify-scope/{profile_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["scope_compliant"] is True
    assert body["violations"] == []
    assert body["token_exposed"] is False
    assert _ALLOWED_SCOPE in body["scope_granted"]


def test_revoke_token():
    profile_id = _create_profile("s19_revoke_profile")
    auth_r = client.post("/v1/oauth/google-calendar/authorize", json={"profile_id": profile_id})
    state = auth_r.json()["state_token"]
    client.get(f"/v1/oauth/google-calendar/callback?code=code&state={state}")
    r = client.post(f"/v1/oauth/google-calendar/revoke/{profile_id}", json={"actor": {"id": "op"}})
    assert r.status_code == 200
    body = r.json()
    assert body["revoked"] is True
    assert body["token_exposed"] is False
    assert body["secret_redacted"] is True
    # Status should be not_authorized after revoke
    status_r = client.get(f"/v1/oauth/google-calendar/status/{profile_id}")
    assert status_r.json()["authorized"] is False


def test_no_token_in_any_response():
    profile_id = _create_profile("s19_no_token_leak_profile")
    auth_r = client.post("/v1/oauth/google-calendar/authorize", json={"profile_id": profile_id})
    state = auth_r.json()["state_token"]
    callback_r = client.get(f"/v1/oauth/google-calendar/callback?code=code&state={state}")
    status_r = client.get(f"/v1/oauth/google-calendar/status/{profile_id}")
    scope_r = client.get(f"/v1/oauth/google-calendar/verify-scope/{profile_id}")
    for r in (auth_r, callback_r, status_r, scope_r):
        body_str = r.text
        assert "placeholder_access_token_redacted" not in body_str
        assert "placeholder_refresh_token_redacted" not in body_str
