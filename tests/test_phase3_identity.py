from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.identity.auth import AuthenticationError, issue_token, verify_token


client = TestClient(app)


def _seed_identity(tenant_id: str = "tenant-phase3") -> dict[str, str]:
    init_db()
    suffix = uuid4().hex
    admin_id = f"user-admin-{suffix}"
    viewer_id = f"user-viewer-{suffix}"
    target_id = f"user-target-{suffix}"
    db = SessionLocal()
    try:
        db.add_all(
            [
                IdentityUser(id=admin_id, email=f"admin-{suffix}@example.test", display_name="Admin"),
                IdentityUser(id=viewer_id, email=f"viewer-{suffix}@example.test", display_name="Viewer"),
                IdentityUser(id=target_id, email=f"target-{suffix}@example.test", display_name="Target"),
                IdentityMembership(
                    id=f"membership-admin-{suffix}",
                    tenant_id=tenant_id,
                    user_id=admin_id,
                    role_name="admin",
                    status="active",
                ),
                IdentityMembership(
                    id=f"membership-viewer-{suffix}",
                    tenant_id=tenant_id,
                    user_id=viewer_id,
                    role_name="viewer",
                    status="active",
                ),
            ]
        )
        db.commit()
    finally:
        db.close()
    return {
        "tenant_id": tenant_id,
        "admin_id": admin_id,
        "viewer_id": viewer_id,
        "target_id": target_id,
    }


@pytest.fixture
def identity_seed(monkeypatch):
    monkeypatch.setattr(settings, "auth_secret", "phase3-test-secret")
    return _seed_identity()


def _headers(user_id: str, tenant_id: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'phase3-test-secret')}"}


def test_token_rejects_tampering_and_expiry():
    token = issue_token("user-1", "tenant-1", "secret", expires_at=100)
    with pytest.raises(AuthenticationError, match="token_expired"):
        verify_token(token, "secret", now=100)
    encoded_payload, encoded_signature = token.split(".", 1)
    tampered_signature = ("A" if encoded_signature[0] != "A" else "B") + encoded_signature[1:]
    with pytest.raises(AuthenticationError, match="invalid_token_signature"):
        verify_token(f"{encoded_payload}.{tampered_signature}", "secret", now=1)


def test_unauthenticated_identity_read_and_mutation_fail(identity_seed):
    assert client.get("/v1/identity/me").status_code == 401
    response = client.post(
        f"/v1/identity/tenants/{identity_seed['tenant_id']}/members",
        json={"user_id": identity_seed["target_id"], "role_name": "operator"},
    )
    assert response.status_code == 401


def test_current_user_is_server_derived(identity_seed):
    response = client.get(
        "/v1/identity/me",
        headers=_headers(identity_seed["admin_id"], identity_seed["tenant_id"]),
    )
    assert response.status_code == 200
    assert response.json() == {
        "user_id": identity_seed["admin_id"],
        "tenant_id": identity_seed["tenant_id"],
        "role_name": "admin",
    }


def test_cross_tenant_and_body_tenant_override_are_blocked(identity_seed):
    headers = _headers(identity_seed["admin_id"], identity_seed["tenant_id"])
    cross_tenant = client.post(
        "/v1/identity/tenants/tenant-other/members",
        headers=headers,
        json={"user_id": identity_seed["target_id"], "role_name": "operator"},
    )
    assert cross_tenant.status_code == 403
    body_override = client.post(
        f"/v1/identity/tenants/{identity_seed['tenant_id']}/members",
        headers=headers,
        json={
            "user_id": identity_seed["target_id"],
            "role_name": "operator",
            "tenant_id": "tenant-other",
            "actor": "attacker",
        },
    )
    assert body_override.status_code == 403


def test_rbac_and_server_actor(identity_seed):
    viewer_response = client.post(
        f"/v1/identity/tenants/{identity_seed['tenant_id']}/members",
        headers=_headers(identity_seed["viewer_id"], identity_seed["tenant_id"]),
        json={"user_id": identity_seed["target_id"], "role_name": "operator"},
    )
    assert viewer_response.status_code == 403

    admin_response = client.post(
        f"/v1/identity/tenants/{identity_seed['tenant_id']}/members",
        headers=_headers(identity_seed["admin_id"], identity_seed["tenant_id"]),
        json={
            "user_id": identity_seed["target_id"],
            "role_name": "operator",
            "actor": "attacker",
        },
    )
    assert admin_response.status_code == 201
    assert admin_response.json()["actor_id"] == identity_seed["admin_id"]
    assert admin_response.json()["tenant_id"] == identity_seed["tenant_id"]
