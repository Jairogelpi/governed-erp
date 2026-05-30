"""API tests for Sprint 76 - Odoo read mapping."""

from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.odoo_connection_test import (
    OdooConnectionTestInput,
    OdooConnectionTestService,
)
from erpguard.product.odoo_read_mapping import OdooReadMappingService
from test_odoo_connection_test import MockOdooConnectionClient, _adapter_session
from test_odoo_read_mapping import MockOdooReadClient


def _passed_connection(db):
    adapter_session = _adapter_session(
        db, session_id=f"csess_odoo_map_api_{uuid4().hex[:8]}"
    )
    return OdooConnectionTestService(
        db,
        connection_client=MockOdooConnectionClient(succeeds=True),
    ).run_test(
        OdooConnectionTestInput(
            adapter_session_id=adapter_session.adapter_session_id,
            requested_by="operator_1",
            allow_network_test=True,
        )
    )


def test_api_creates_blocked_mapping():
    init_db()
    db = SessionLocal()
    connection = _passed_connection(db)
    db.close()
    client = TestClient(app)

    response = client.post(
        f"/v1/operator-console/connectors/odoo-connection-test/{connection.connection_test_id}/read-mapping",
        json={
            "requested_by": "operator_1",
            "object_type": "sale_order",
            "lookup": {"reference": "S00001"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "business_read_not_allowed" in payload["blocking_reasons"]


def test_api_creates_mocked_passed_mapping(monkeypatch):
    init_db()
    db = SessionLocal()
    connection = _passed_connection(db)
    db.close()

    monkeypatch.setattr(
        OdooReadMappingService,
        "_default_read_client",
        lambda self: MockOdooReadClient({"partner": {"id": 9, "display_name": "Acme"}}),
    )
    client = TestClient(app)

    response = client.post(
        f"/v1/operator-console/connectors/odoo-connection-test/{connection.connection_test_id}/read-mapping",
        json={
            "requested_by": "operator_1",
            "object_type": "partner",
            "lookup": {"id": 9},
            "allow_business_read": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "passed"
    assert payload["canonical_object"]["object_type"] == "partner"
    assert payload["business_data_read"] is True


def test_api_retrieves_lists_and_returns_audit(monkeypatch):
    init_db()
    db = SessionLocal()
    connection = _passed_connection(db)
    db.close()
    monkeypatch.setattr(
        OdooReadMappingService,
        "_default_read_client",
        lambda self: MockOdooReadClient({"product": {"id": 3, "display_name": "Kit"}}),
    )
    client = TestClient(app)
    created = client.post(
        f"/v1/operator-console/connectors/odoo-connection-test/{connection.connection_test_id}/read-mapping",
        json={
            "requested_by": "operator_1",
            "object_type": "product",
            "lookup": {"id": 3},
            "allow_business_read": True,
        },
    ).json()

    retrieved = client.get(
        f"/v1/operator-console/connectors/odoo-read-mapping/{created['read_mapping_id']}"
    )
    listed = client.get("/v1/operator-console/connectors/odoo-read-mappings")
    audit = client.get("/v1/operator-console/connectors/odoo-read-mapping-audit")

    assert retrieved.status_code == 200
    assert retrieved.json()["read_mapping_id"] == created["read_mapping_id"]
    assert listed.status_code == 200
    assert any(
        item["read_mapping_id"] == created["read_mapping_id"]
        for item in listed.json()["read_mappings"]
    )
    assert audit.status_code == 200
    assert any(event["event_type"] == "odoo_read_mapping_passed" for event in audit.json()["events"])
