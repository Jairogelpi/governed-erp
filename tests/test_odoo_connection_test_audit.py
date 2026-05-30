"""Audit tests for Sprint 75 - Odoo connection test."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.product.odoo_connection_test import (
    OdooConnectionTestAuditService,
    OdooConnectionTestInput,
    OdooConnectionTestService,
)
from test_odoo_connection_test import MockOdooConnectionClient, _adapter_session


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_audit_records_passed_connection_test():
    db = _db()
    adapter_session = _adapter_session(db)

    OdooConnectionTestService(
        db,
        connection_client=MockOdooConnectionClient(succeeds=True),
    ).run_test(
        OdooConnectionTestInput(
            adapter_session_id=adapter_session.adapter_session_id,
            requested_by="operator_1",
            allow_network_test=True,
        )
    )

    events = OdooConnectionTestAuditService(db).get_audit().events

    assert any(event["event_type"] == "odoo_connection_test_requested" for event in events)
    assert any(event["event_type"] == "odoo_connection_test_passed" for event in events)


def test_audit_records_blocked_connection_test():
    db = _db()
    adapter_session = _adapter_session(db)

    OdooConnectionTestService(db).run_test(
        OdooConnectionTestInput(
            adapter_session_id=adapter_session.adapter_session_id,
            requested_by="operator_1",
            allow_network_test=False,
        )
    )

    events = OdooConnectionTestAuditService(db).get_audit().events

    assert any(event["event_type"] == "odoo_connection_test_blocked" for event in events)


def test_audit_does_not_contain_raw_secret():
    db = _db()
    adapter_session = _adapter_session(db, secret="raw-secret-for-audit-test")

    OdooConnectionTestService(
        db,
        connection_client=MockOdooConnectionClient(succeeds=True),
    ).run_test(
        OdooConnectionTestInput(
            adapter_session_id=adapter_session.adapter_session_id,
            requested_by="operator_1",
            allow_network_test=True,
        )
    )

    payload = str(OdooConnectionTestAuditService(db).get_audit().events)

    assert "raw-secret-for-audit-test" not in payload
    assert "password" not in payload.lower()
    assert "api_key" not in payload.lower()
    assert "token" not in payload.lower()
    assert "secret" not in payload.lower()
