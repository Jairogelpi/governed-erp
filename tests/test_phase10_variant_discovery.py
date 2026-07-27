from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal, init_db
from erpguard.domain.events.ocel_service import OcelEventService
from erpguard.domain.identity.auth import issue_token
from erpguard.domain.variants.discovery import VariantDiscoveryService


def _document() -> dict:
    return {
        "ocel:objects": {
            "so-1": {"ocel:type": "sale_order", "ocel:ovmap": {}},
            "so-2": {"ocel:type": "sale_order", "ocel:ovmap": {}},
            "so-3": {"ocel:type": "sale_order", "ocel:ovmap": {}},
            "so-empty": {"ocel:type": "sale_order", "ocel:ovmap": {}},
        },
        "ocel:events": {
            "e-1": {"ocel:activity": "quote.created", "ocel:timestamp": "2026-01-01T00:00:00Z", "ocel:omap": ["so-1"], "ocel:vmap": {}},
            "e-2": {"ocel:activity": "quote.reviewed", "ocel:timestamp": "2026-01-01T00:01:00Z", "ocel:omap": ["so-1"], "ocel:vmap": {}},
            "e-3": {"ocel:activity": "order.created", "ocel:timestamp": "2026-01-01T00:02:00Z", "ocel:omap": ["so-1"], "ocel:vmap": {}},
            "e-4": {"ocel:activity": "quote.created", "ocel:timestamp": "2026-01-01T00:00:00Z", "ocel:omap": ["so-2"], "ocel:vmap": {}},
            "e-5": {"ocel:activity": "order.created", "ocel:timestamp": "2026-01-01T00:03:00Z", "ocel:omap": ["so-2"], "ocel:vmap": {}},
            "e-6": {"ocel:activity": "quote.created", "ocel:timestamp": "2026-01-01T00:00:00Z", "ocel:omap": ["so-3"], "ocel:vmap": {}},
        },
    }


def test_variant_discovery_groups_sequences_and_calculates_duration():
    init_db()
    tenant = f"phase10-{uuid4().hex}"
    db = SessionLocal()
    try:
        OcelEventService(db).import_ocel(tenant_id=tenant, document=_document(), source="fixture")
        service = VariantDiscoveryService(db)
        variants = service.discover(tenant_id=tenant, object_type="sales_order")
        assert [(item.sequence, item.case_count) for item in variants] == [
            (("sales.quote.created", "sales.quote.reviewed", "sales.order.created"), 1),
            (("sales.quote.created", "sales.order.created"), 1),
            (("sales.quote.created",), 1),
        ]
        assert variants[0].duration_seconds == 120.0
        assert variants[1].duration_seconds == 180.0
        assert all("so-empty" not in item.case_ids for item in variants)
        trace = service.case_trace(tenant_id=tenant, case_id="so-1", object_type="sales_order")
        assert [event.event_type for event in trace.events] == [
            "sales.quote.created", "sales.quote.reviewed", "sales.order.created"
        ]
    finally:
        db.close()


def test_variant_api_is_tenant_scoped_and_dashboard_is_present(monkeypatch):
    init_db()
    monkeypatch.setattr(settings, "auth_secret", "phase10-auth")
    tenant = f"phase10-api-{uuid4().hex}"
    suffix = uuid4().hex
    user = f"phase10-admin-{suffix}"
    db = SessionLocal()
    db.add(IdentityUser(id=user, email=f"{suffix}@example.test", display_name="Phase 10"))
    db.add(IdentityMembership(id=f"phase10-membership-{suffix}", tenant_id=tenant, user_id=user, role_name="admin", status="active"))
    db.commit()
    OcelEventService(db).import_ocel(tenant_id=tenant, document=_document(), source="fixture")
    db.close()
    headers = {"Authorization": f"Bearer {issue_token(user, tenant, 'phase10-auth')}"}
    client = TestClient(app)
    response = client.get("/v1/variants?object_type=sales_order", headers=headers)
    assert response.status_code == 200
    assert response.json()[0]["case_count"] == 1
    trace = client.get("/v1/variants/cases/so-1?object_type=sales_order", headers=headers)
    assert trace.status_code == 200
    assert trace.json()["case_id"] == "so-1"
    dashboard = client.get("/v1/variants/dashboard", headers=headers)
    assert dashboard.status_code == 200
    assert "Variant Discovery" in dashboard.text
