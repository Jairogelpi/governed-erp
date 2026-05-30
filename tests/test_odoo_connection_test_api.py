"""API tests for Sprint 75 - Odoo connection test."""

from fastapi.testclient import TestClient
from uuid import uuid4

from apps.api.main import app
from erpguard.db.session import init_db
from erpguard.db.session import SessionLocal
from erpguard.product.odoo_connection_test import OdooConnectionTestService
from test_odoo_connection_test import MockOdooConnectionClient, _adapter_session


def test_api_runs_blocked_test_by_default():
    init_db()
    db = SessionLocal()
    adapter_session = _adapter_session(db, session_id=f"csess_odoo_ct_api_blocked_{uuid4().hex[:8]}")
    db.close()
    client = TestClient(app)

    response = client.post(
        f"/v1/operator-console/connectors/odoo-adapter-session/{adapter_session.adapter_session_id}/connection-test",
        json={"requested_by": "operator_1"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert "network_test_not_allowed" in payload["blocking_reasons"]
    assert payload["external_http_performed"] is False


def test_api_runs_mocked_allowed_test(monkeypatch):
    init_db()
    db = SessionLocal()
    adapter_session = _adapter_session(db, session_id=f"csess_odoo_ct_api_allowed_{uuid4().hex[:8]}")
    db.close()

    def fake_client(self):
        return MockOdooConnectionClient(succeeds=True, version="19.0-api")

    monkeypatch.setattr(OdooConnectionTestService, "_default_connection_client", fake_client)
    client = TestClient(app)

    response = client.post(
        f"/v1/operator-console/connectors/odoo-adapter-session/{adapter_session.adapter_session_id}/connection-test",
        json={"requested_by": "operator_1", "allow_network_test": True},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "passed"
    assert payload["odoo_server_version"] == "19.0-api"
    assert payload["business_data_read"] is False


def test_api_retrieves_lists_and_returns_audit(monkeypatch):
    init_db()
    db = SessionLocal()
    adapter_session = _adapter_session(db, session_id=f"csess_odoo_ct_api_get_{uuid4().hex[:8]}")
    db.close()

    monkeypatch.setattr(
        OdooConnectionTestService,
        "_default_connection_client",
        lambda self: MockOdooConnectionClient(succeeds=True),
    )
    client = TestClient(app)
    created = client.post(
        f"/v1/operator-console/connectors/odoo-adapter-session/{adapter_session.adapter_session_id}/connection-test",
        json={"requested_by": "operator_1", "allow_network_test": True},
    ).json()

    retrieved = client.get(
        f"/v1/operator-console/connectors/odoo-connection-test/{created['connection_test_id']}"
    )
    listed = client.get("/v1/operator-console/connectors/odoo-connection-tests")
    audit = client.get("/v1/operator-console/connectors/odoo-connection-test-audit")

    assert retrieved.status_code == 200
    assert retrieved.json()["connection_test_id"] == created["connection_test_id"]
    assert listed.status_code == 200
    assert any(
        item["connection_test_id"] == created["connection_test_id"]
        for item in listed.json()["connection_tests"]
    )
    assert audit.status_code == 200
    assert any(
        event["event_type"] == "odoo_connection_test_passed"
        for event in audit.json()["events"]
    )
