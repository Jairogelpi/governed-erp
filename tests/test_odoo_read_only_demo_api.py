"""API tests for Sprint 79 - Odoo read-only demo flow."""

from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.odoo_read_only_demo_flow import OdooReadOnlyDemoFlowService
from test_odoo_connection_test import MockOdooConnectionClient
from test_odoo_read_mapping import MockOdooReadClient
from test_odoo_read_only_adapter_shell import _activation
from test_odoo_read_only_demo_flow import DEMO_PAYLOADS


def test_api_runs_retrieves_lists_and_returns_audit(monkeypatch):
    init_db()
    db = SessionLocal()
    activation = _activation(db, session_id=f"csess_demo_api_{uuid4().hex[:8]}")
    db.close()

    monkeypatch.setattr(
        OdooReadOnlyDemoFlowService,
        "_default_connection_client",
        lambda self: MockOdooConnectionClient(succeeds=True),
    )
    monkeypatch.setattr(
        OdooReadOnlyDemoFlowService,
        "_default_read_client",
        lambda self: MockOdooReadClient(DEMO_PAYLOADS),
    )
    client = TestClient(app)

    created = client.post(
        f"/v1/operator-console/connectors/read-only-activation/{activation.activation_id}/odoo-read-only-demo-flow",
        json={
            "requested_by": "operator_1",
            "object_types": ["partner", "product", "sale_order"],
            "allow_network_test": True,
            "allow_business_read": True,
        },
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["status"] == "completed"
    retrieved = client.get(
        f"/v1/operator-console/connectors/odoo-read-only-demo-flow/{payload['demo_flow_id']}"
    )
    listed = client.get("/v1/operator-console/connectors/odoo-read-only-demo-flows")
    audit = client.get("/v1/operator-console/connectors/odoo-read-only-demo-audit")

    assert retrieved.status_code == 200
    assert retrieved.json()["demo_flow_id"] == payload["demo_flow_id"]
    assert listed.status_code == 200
    assert any(item["demo_flow_id"] == payload["demo_flow_id"] for item in listed.json()["demo_flows"])
    assert audit.status_code == 200
    assert any(
        event["event_type"] == "odoo_read_only_demo_flow_completed"
        for event in audit.json()["events"]
    )
