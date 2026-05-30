"""API tests for Sprint 78 - Odoo read evidence packs."""

from uuid import uuid4

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import SessionLocal, init_db
from test_odoo_read_evidence_pack import PAYLOADS
from test_odoo_read_mapping import MockOdooReadClient, _map, _passed_connection_test


def _mapping(db):
    connection = _passed_connection_test(db, session_id=f"csess_ev_api_{uuid4().hex[:8]}")
    return _map(
        db,
        connection.connection_test_id,
        object_type="product",
        lookup={"id": 2},
        allow=True,
        client=MockOdooReadClient({"product": PAYLOADS["product"]}),
    )


def test_api_creates_retrieves_lists_and_returns_audit():
    init_db()
    db = SessionLocal()
    mapping = _mapping(db)
    db.close()
    client = TestClient(app)

    created = client.post(
        f"/v1/operator-console/connectors/odoo-read-mapping/{mapping.read_mapping_id}/evidence-pack",
        json={"created_by": "operator_1"},
    )
    assert created.status_code == 200
    payload = created.json()
    assert payload["status"] == "created"
    assert payload["safety_summary"]["read_client_called"] is False

    retrieved = client.get(
        f"/v1/operator-console/connectors/odoo-read-evidence-pack/{payload['evidence_pack_id']}"
    )
    listed = client.get("/v1/operator-console/connectors/odoo-read-evidence-packs")
    audit = client.get("/v1/operator-console/connectors/odoo-read-evidence-audit")

    assert retrieved.status_code == 200
    assert retrieved.json()["evidence_pack_id"] == payload["evidence_pack_id"]
    assert listed.status_code == 200
    assert any(
        item["evidence_pack_id"] == payload["evidence_pack_id"]
        for item in listed.json()["evidence_packs"]
    )
    assert audit.status_code == 200
    assert any(
        event["event_type"] == "odoo_read_evidence_pack_created"
        for event in audit.json()["events"]
    )
