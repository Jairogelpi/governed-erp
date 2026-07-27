from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.odoo_bridge import OdooBridgeEvent, OdooEventIngestionService
from erpguard.domain.identity.auth import issue_token


def _event(event_id: str = "evt-1") -> dict:
    return {
        "event_id": event_id,
        "event_type": "sale.order.created",
        "model": "sale.order",
        "record_id": 42,
        "occurred_at": "2026-07-28T12:00:00Z",
        "values": {"name": "SO-042", "amount_total": 50},
        "correlation_id": "corr-42",
        "historical": True,
        "synthetic": False,
    }


def test_odoo_bridge_normalizes_idempotently_and_preserves_labels():
    init_db()
    tenant_id = f"tenant-8-{uuid4().hex}"
    db = SessionLocal()
    try:
        service = OdooEventIngestionService(db)
        first = service.ingest_event(tenant_id=tenant_id, payload=_event())
        retry = service.ingest_event(tenant_id=tenant_id, payload=_event())
        assert first.created_events == 1
        assert retry.duplicate_events == 1
        assert first.correlation_id == "corr-42"
        exported = service.export_events(tenant_id=tenant_id)
        event = next(iter(exported["ocel:events"].values()))
        assert event["ocel:activity"] == "sales.quote.created"
        assert event["ocel:vmap"]["historical"] is True
        assert event["ocel:vmap"]["synthetic"] is False
        assert event["ocel:vmap"]["correlation_id"] == "corr-42"
        obj = next(iter(exported["ocel:objects"].values()))
        assert obj["ocel:type"] == "sales_order"
        assert obj["ocel:ovmap"]["native"]["model"] == "sale.order"
    finally:
        db.close()


def test_bridge_rejects_unsupported_write_like_event():
    try:
        OdooBridgeEvent.model_validate({**_event(), "event_type": "sale.order.confirm"})
    except ValueError as exc:
        assert "unsupported_event_type" in str(exc)
    else:
        raise AssertionError("write-like bridge event was accepted")


def _identity(tenant_id: str) -> dict[str, str]:
    suffix = uuid4().hex
    user_id = f"phase8-admin-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user_id, email=f"{suffix}@example.test", display_name="Phase 8"))
    db.add(IdentityMembership(
        id=f"phase8-membership-{suffix}", tenant_id=tenant_id, user_id=user_id,
        role_name="admin", status="active",
    ))
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {issue_token(user_id, tenant_id, 'phase8-auth')}"}


def test_bridge_webhook_and_poll_are_tenant_scoped(monkeypatch):
    init_db()
    monkeypatch.setattr(settings, "auth_secret", "phase8-auth")
    client = TestClient(app)
    headers_a = _identity("tenant-8-a")
    headers_b = _identity("tenant-8-b")
    response = client.post("/v1/events/odoo/webhook", headers=headers_a, json=_event("api-event"))
    assert response.status_code == 201
    assert response.json()["correlation_id"] == "corr-42"
    poll = client.post(
        "/v1/events/odoo/poll",
        headers=headers_a,
        json={"events": [_event("poll-event")], "cursor": "cursor-2"},
    )
    assert poll.status_code == 201
    assert poll.json()["cursor"] == "cursor-2"
    assert client.get("/v1/events/ocel/export", headers=headers_b).json()["ocel:events"] == {}
