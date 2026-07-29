from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.models import (
    AuditEvent,
    Connection,
    Policy,
)
from erpguard.db.session import init_db


def test_health_endpoint_returns_ok():
    client = TestClient(app)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_database_models_import_cleanly():
    assert Connection.__tablename__ == "connections"
    assert AuditEvent.__tablename__ == "audit_events"
    assert Policy.__tablename__ == "policies"


def test_database_schema_can_be_initialized():
    init_db()
