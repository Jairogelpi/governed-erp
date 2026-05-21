from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_demo_contains_connector_credential_vault_section():
    html = client.get("/demo").text

    assert "Connector Credential Vault" in html
    assert "connectorAuthProfileOutput" in html
    assert "connectorAuthAuditOutput" in html
    assert "/v1/connectors/auth-profiles" in html
    assert "/v1/connectors/scopes" in html


def test_demo_connector_auth_safety_copy_keeps_no_goals_visible():
    html = client.get("/demo").text

    assert "No real OAuth flow" in html
    assert "No external connector API calls" in html
    assert "Secrets are redacted" in html
