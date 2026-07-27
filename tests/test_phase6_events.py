from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.fake_generator import build_fake_ocel
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.identity.auth import issue_token


def _ocel(suffix: str) -> dict:
    return {
        "ocel:global-event": {"ocel:activity": "erpguard.test", "ocel:timestamp": "2026-07-28T10:00:00Z"},
        "ocel:events": {
            f"e-{suffix}": {
                "ocel:activity": "sales.order.created",
                "ocel:timestamp": "2026-07-28T10:00:00Z",
                "ocel:omap": [f"o-{suffix}"],
                "ocel:vmap": {"amount": 100},
            }
        },
        "ocel:objects": {
            f"o-{suffix}": {
                "ocel:type": "sale_order",
                "ocel:ovmap": {"name": "SO-001"},
            }
        },
    }


def test_ocel_import_is_idempotent_and_export_round_trips():
    init_db()
    tenant = f"phase6-{uuid4().hex}"
    db = SessionLocal()
    try:
        service = OcelEventService(db)
        first = service.import_ocel(tenant_id=tenant, document=_ocel("one"), source="test")
        second = service.import_ocel(tenant_id=tenant, document=_ocel("one"), source="test")
        assert first.created_events == 1
        assert first.created_objects == 1
        assert second.duplicate_events == 1
        assert second.created_events == 0
        exported = service.export_ocel(tenant_id=tenant)
        assert list(exported["ocel:events"]) == ["e-one"]
        assert list(exported["ocel:objects"]) == ["o-one"]
    finally:
        db.close()


def test_ingestion_cursor_is_tenant_scoped():
    init_db()
    db = SessionLocal()
    try:
        service = OcelEventService(db)
        service.save_cursor(tenant_id="tenant-a", connector_id="fake", stream_key="orders", value="2")
        service.save_cursor(tenant_id="tenant-b", connector_id="fake", stream_key="orders", value="9")
        assert service.get_cursor("tenant-a", "fake", "orders") == "2"
        assert service.get_cursor("tenant-b", "fake", "orders") == "9"
    finally:
        db.close()


def _seed_identity(tenant_id: str) -> tuple[str, dict[str, str]]:
    suffix = uuid4().hex
    user_id = f"phase6-admin-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Phase 6"))
    db.add(IdentityMembership(
        id=f"phase6-membership-{suffix}", tenant_id=tenant_id, user_id=user_id,
        role_name="admin", status="active",
    ))
    db.commit()
    db.close()
    return user_id, {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'phase6-auth')}"}


def test_event_api_is_tenant_scoped_and_fake_generation_is_deterministic(monkeypatch):
    init_db()
    monkeypatch.setattr(settings, "auth_secret", "phase6-auth")
    tenant_a = f"api-a-{uuid4().hex}"
    tenant_b = f"api-b-{uuid4().hex}"
    _, headers_a = _seed_identity(tenant_a)
    _, headers_b = _seed_identity(tenant_b)
    client = TestClient(app)

    response = client.post("/v1/events/fake-generate", headers=headers_a)
    assert response.status_code == 201
    assert response.json()["created_events"] == 2
    assert client.get("/v1/events/ocel/export", headers=headers_a).json()["ocel:events"]
    assert client.get("/v1/events/ocel/export", headers=headers_b).json()["ocel:events"] == {}

    generated = build_fake_ocel(tenant_id=tenant_a)
    assert generated["ocel:global-event"]["ocel:activity"] == "erpguard.fake"
