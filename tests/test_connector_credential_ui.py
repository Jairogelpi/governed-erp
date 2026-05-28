"""Tests for Sprint 55 — Connector Credential Vault UI on /demo."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_ui_exposes_credential_vault_card():
    response = client.get("/demo")
    assert response.status_code == 200
    assert b"Credential Vault Contract" in response.content
    assert b"Sprint 55" in response.content
    assert b"credVaultSeal" in response.content
    assert b"credVaultGetMetadata" in response.content
    assert b"credVaultAudit" in response.content
    assert b"credVaultRevoke" in response.content


def test_ui_credential_vault_has_auth_type_select():
    response = client.get("/demo")
    assert response.status_code == 200
    assert b"credVaultAuthType" in response.content
    assert b"password" in response.content
    assert b"api_key" in response.content
    assert b"token" in response.content


def test_ui_credential_vault_has_secret_input():
    response = client.get("/demo")
    assert response.status_code == 200
    assert b"credVaultSecret" in response.content
    assert b"credVaultSessionId" in response.content


def test_ui_credential_vault_safety_banner():
    response = client.get("/demo")
    assert response.status_code == 200
    assert (
        b"never returns raw secrets" in response.content
        or b"does not connect to the ERP" in response.content
    )
