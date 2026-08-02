"""Spec 94 -- the internal dev-token bootstrap: issues a real, verifiable
bearer token, and is never mounted in the public (non-internal) app."""

from __future__ import annotations

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.app_factory import create_app, create_public_app
from erpguard.config import settings
from erpguard.db.session import init_db


def _setup(monkeypatch) -> None:
    monkeypatch.setattr(settings, "auth_secret", "dev-token-test-secret")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()


def test_dev_token_issues_a_working_bearer_token(monkeypatch):
    _setup(monkeypatch)
    client = TestClient(create_app(include_internal=True))

    resp = client.post("/internal/dev-tokens", json={"tenant_id": "web-app-tenant"})
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["tenant_id"] == "web-app-tenant"
    assert body["role_name"] == "admin"

    me = client.get("/v1/identity/me", headers={"Authorization": f"Bearer {body['token']}"})
    assert me.status_code == 200, me.text
    assert me.json()["tenant_id"] == "web-app-tenant"


def test_dev_tokens_not_mounted_in_the_default_public_app():
    app = create_public_app(include_internal=False)
    assert "/internal/dev-tokens" not in app.openapi()["paths"]


def test_dev_token_rejects_invalid_role(monkeypatch):
    _setup(monkeypatch)
    client = TestClient(create_app(include_internal=True))
    resp = client.post("/internal/dev-tokens", json={"tenant_id": "t", "role_name": "superuser"})
    assert resp.status_code == 422
