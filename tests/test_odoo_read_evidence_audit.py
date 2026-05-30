"""Audit tests for Sprint 78 - Odoo read evidence packs."""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.product.odoo_read_evidence_pack import (
    OdooReadEvidenceAuditService,
    OdooReadEvidencePackInput,
    OdooReadEvidencePackService,
)
from test_odoo_read_evidence_pack import _passed_mapping


def _db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return Session()


def test_audit_records_created_and_does_not_contain_raw_secret():
    db = _db()
    mapping = _passed_mapping(db, "partner")

    OdooReadEvidencePackService(db).create_pack(
        OdooReadEvidencePackInput(read_mapping_id=mapping.read_mapping_id)
    )

    events = OdooReadEvidenceAuditService(db).get_audit().events
    payload = str(events).lower()

    assert any(event["event_type"] == "odoo_read_evidence_pack_created" for event in events)
    assert "password" not in payload
    assert "api_key" not in payload
    assert "token" not in payload
    assert "secret" not in payload
