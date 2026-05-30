"""Audit tests for Sprint 76 - Odoo read mapping."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.product.odoo_read_mapping import (
    OdooReadMappingAuditService,
    OdooReadMappingInput,
    OdooReadMappingService,
)
from test_odoo_read_mapping import MockOdooReadClient, _passed_connection_test


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_audit_records_passed_mapping():
    db = _db()
    connection = _passed_connection_test(db)

    OdooReadMappingService(
        db,
        read_client=MockOdooReadClient({"partner": {"id": 1, "display_name": "A"}}),
    ).run_mapping(
        OdooReadMappingInput(
            connection_test_id=connection.connection_test_id,
            requested_by="operator_1",
            object_type="partner",
            lookup={"id": 1},
            allow_business_read=True,
        )
    )

    events = OdooReadMappingAuditService(db).get_audit().events

    assert any(event["event_type"] == "odoo_read_mapping_requested" for event in events)
    assert any(event["event_type"] == "odoo_read_mapping_passed" for event in events)


def test_audit_records_blocked_mapping():
    db = _db()
    connection = _passed_connection_test(db)

    OdooReadMappingService(db).run_mapping(
        OdooReadMappingInput(
            connection_test_id=connection.connection_test_id,
            requested_by="operator_1",
            object_type="payment",
            lookup={"id": 1},
            allow_business_read=True,
        )
    )

    events = OdooReadMappingAuditService(db).get_audit().events

    assert any(event["event_type"] == "odoo_read_mapping_blocked" for event in events)


def test_audit_does_not_contain_raw_secret_or_unredacted_extra_fields():
    db = _db()
    connection = _passed_connection_test(db, secret="raw-secret-for-read-map")

    OdooReadMappingService(
        db,
        read_client=MockOdooReadClient(
            {"partner": {"id": 1, "display_name": "A", "password": "leaky"}}
        ),
    ).run_mapping(
        OdooReadMappingInput(
            connection_test_id=connection.connection_test_id,
            requested_by="operator_1",
            object_type="partner",
            lookup={"id": 1},
            allow_business_read=True,
        )
    )

    payload = str(OdooReadMappingAuditService(db).get_audit().events)

    assert "raw-secret-for-read-map" not in payload
    assert "leaky" not in payload
    assert "password': 'leaky" not in payload
    assert "api_key" not in payload.lower()
    assert "token" not in payload.lower()
