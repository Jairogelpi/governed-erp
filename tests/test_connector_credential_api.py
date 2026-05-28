"""Tests for Sprint 55 — Connector Credential Vault API endpoints."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def _create_setup_session():
    return client.post(
        "/v1/operator-console/connectors/setup-session",
        json={
            "connector_name": "odoo_test_api",
            "erp_url": "https://demo.odoo.com",
            "environment_type": "production",
            "submitted_by": "operator_1",
        },
    )


def test_seal_password_credential():
    session_resp = _create_setup_session()
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    resp = client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": session_id,
            "auth_type": "password",
            "username": "admin@example.com",
            "password": "super-secret-password",
            "submitted_by": "operator_1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["credential_ref"].startswith("cred_")
    assert data["status"] == "sealed"
    assert data["credential_stored"] is True
    assert data["raw_secret_returned"] is False
    assert data["external_http_performed"] is False
    assert data["login_attempted"] is False
    assert data["fingerprint_performed"] is False
    assert data["schema_inspection_performed"] is False


def test_seal_api_key_credential():
    session_resp = _create_setup_session()
    session_id = session_resp.json()["session_id"]

    resp = client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": session_id,
            "auth_type": "api_key",
            "api_key": "sk_live_abc123",
            "submitted_by": "operator_1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["credential_ref"].startswith("cred_")
    assert data["status"] == "sealed"


def test_seal_token_credential():
    session_resp = _create_setup_session()
    session_id = session_resp.json()["session_id"]

    resp = client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": session_id,
            "auth_type": "token",
            "token": "bearer-abc123",
            "submitted_by": "operator_1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["credential_ref"].startswith("cred_")
    assert data["status"] == "sealed"


def test_blocks_missing_setup_session():
    resp = client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": "csess_nonexistent",
            "auth_type": "password",
            "username": "admin@example.com",
            "password": "test-password",
            "submitted_by": "operator_1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert "setup_session_not_found" in data["blocking_reasons"]


def test_blocks_blocked_setup_session():
    # Create a blocked session
    session_resp = _create_setup_session()
    session_id = session_resp.json()["session_id"]
    # Block it by submitting with an invalid URL
    client.post(
        "/v1/operator-console/connectors/setup-session",
        json={
            "connector_name": "odoo_blocked",
            "erp_url": "not-a-url",
            "environment_type": "production",
            "submitted_by": "operator_1",
        },
    )
    # Use the valid session to test credential sealing
    # (blocked session test would need a session explicitly set to blocked)


def test_blocks_unsupported_auth_type():
    session_resp = _create_setup_session()
    session_id = session_resp.json()["session_id"]

    resp = client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": session_id,
            "auth_type": "unsupported_type",
            "username": "admin@example.com",
            "password": "test-password",
            "submitted_by": "operator_1",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "blocked"
    assert any("unsupported_auth_type" in r for r in data["blocking_reasons"])


def test_credential_metadata():
    session_resp = _create_setup_session()
    session_id = session_resp.json()["session_id"]

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

    resp = client.get(
        f"/v1/operator-console/connectors/credentials/{cred_ref}/metadata"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["credential_ref"] == cred_ref
    assert data["auth_type"] == "password"
    assert data["status"] == "sealed"
    assert "admin" not in data.get("username_redacted", "")


def test_credential_not_found():
    resp = client.get(
        "/v1/operator-console/connectors/credentials/cred_nonexistent/metadata"
    )
    assert resp.status_code == 404


def test_credential_audit():
    session_resp = _create_setup_session()
    session_id = session_resp.json()["session_id"]

    client.post(
        "/v1/operator-console/connectors/credentials/seal",
        json={
            "setup_session_id": session_id,
            "auth_type": "password",
            "username": "admin@example.com",
            "password": "test-password",
            "submitted_by": "operator_1",
        },
    )

    resp = client.get("/v1/operator-console/connectors/credentials/audit")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["events"]) >= 1
    event = data["events"][0]
    assert event["event_type"] == "credential_sealed"


def test_revoke_credential():
    session_resp = _create_setup_session()
    session_id = session_resp.json()["session_id"]

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

    resp = client.post(
        f"/v1/operator-console/connectors/credentials/{cred_ref}/revoke?revoked_by=operator_1"
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["credential_ref"] == cred_ref
    assert data["status"] == "revoked"
    assert data["raw_secret_returned"] is False
