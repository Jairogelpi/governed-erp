from __future__ import annotations

import json
from uuid import uuid4

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.connections import EncryptedSecret, UnifiedConnection
from erpguard.db.models import Connection
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.connections.legacy_migration import migrate_legacy_connections
from erpguard.domain.identity.auth import issue_token
from erpguard.infrastructure.secrets import (
    EncryptedLocalSecretProvider,
    SecretProviderConfigurationError,
)


client = TestClient(app)


def _seed(monkeypatch, tenant_id: str = "tenant-phase4") -> dict[str, str]:
    from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser

    monkeypatch.setattr(settings, "auth_secret", "phase4-auth-secret")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    suffix = uuid4().hex
    user_id = f"phase4-admin-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Phase 4"))
    db.add(IdentityMembership(
        id=f"phase4-membership-{suffix}", tenant_id=tenant_id, user_id=user_id,
        role_name="admin", status="active",
    ))
    db.commit()
    db.close()
    return {"tenant_id": tenant_id, "user_id": user_id}


def _headers(seed: dict[str, str]) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_token(seed['user_id'], seed['tenant_id'], 'phase4-auth-secret')}"}


def test_local_secret_provider_encrypts_and_round_trips():
    provider = EncryptedLocalSecretProvider(Fernet.generate_key())
    sealed = provider.seal("do-not-persist-me")
    assert "do-not-persist-me" not in sealed.ciphertext
    assert provider.reveal(sealed.ciphertext) == "do-not-persist-me"
    assert sealed.fingerprint.startswith("sha256:")


def test_local_secret_provider_requires_key():
    with pytest.raises(SecretProviderConfigurationError, match="local_secret_key_required"):
        EncryptedLocalSecretProvider(None)


def test_unified_connection_api_is_tenant_scoped_and_redacts_secret(monkeypatch):
    init_db()
    seed = _seed(monkeypatch)
    secret = "phase4-api-key"
    response = client.post(
        "/v1/unified/connections",
        headers=_headers(seed),
        json={
            "name": f"Odoo {uuid4().hex}",
            "connector_type": "odoo",
            "endpoint": "https://odoo.example.test",
            "auth_type": "api_key",
            "secret": secret,
            "metadata": {"database": "demo"},
        },
    )
    assert response.status_code == 201
    assert secret not in response.text
    body = response.json()
    assert body["secret_redacted"] is True
    assert body["metadata"] == {"database": "demo"}

    db = SessionLocal()
    try:
        stored_secret = db.get(EncryptedSecret, body["secret_ref"])
        stored_connection = db.get(UnifiedConnection, body["id"])
        assert stored_secret is not None
        assert secret not in stored_secret.ciphertext
        assert stored_connection.tenant_id == seed["tenant_id"]
    finally:
        db.close()

    listed = client.get("/v1/unified/connections", headers=_headers(seed))
    assert listed.status_code == 200
    assert secret not in listed.text
    assert listed.json()[0]["id"] == body["id"]


def test_legacy_connection_path_is_flagged_deprecated():
    response = client.get("/v1/connections")
    assert response.status_code == 200
    assert response.headers["Deprecation"] == "true"
    assert "/v1/unified/connections" in response.headers["Link"]


def test_legacy_migration_encrypts_and_redacts_config(monkeypatch):
    init_db()
    provider = EncryptedLocalSecretProvider(Fernet.generate_key())
    db = SessionLocal()
    legacy = Connection(
        id=f"legacy-{uuid4().hex}", erp_type="odoo", name="Legacy Odoo",
        config_json=json.dumps({"url": "https://odoo.test", "api_key": "legacy-secret"}),
        status="active",
    )
    db.add(legacy)
    db.commit()
    assert migrate_legacy_connections(db, provider) >= 1
    db.refresh(legacy)
    assert "legacy-secret" not in legacy.config_json
    migrated = db.get(UnifiedConnection, f"uconn_legacy_{legacy.id}")
    assert migrated is not None
    encrypted = db.get(EncryptedSecret, migrated.secret_ref)
    assert encrypted is not None
    assert provider.reveal(encrypted.ciphertext) == "legacy-secret"
    db.close()
