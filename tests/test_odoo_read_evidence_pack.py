"""Tests for Sprint 78 - Odoo read evidence packs."""

import json

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import get_odoo_read_mapping_by_id
from erpguard.product.odoo_read_evidence_pack import (
    OdooReadEvidencePackInput,
    OdooReadEvidencePackService,
)
from test_odoo_read_mapping import MockOdooReadClient, _map, _passed_connection_test


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


PAYLOADS = {
    "partner": {"id": 1, "display_name": "Acme"},
    "product": {"id": 2, "display_name": "Kit"},
    "sale_order": {"id": 3, "name": "S00001"},
    "invoice": {"id": 4, "name": "INV/2026/001"},
    "stock_item": {"id": 5, "display_name": "WH/Stock - SKU"},
    "manufacturing_order": {"id": 6, "name": "MO/2026/001"},
}
LOOKUPS = {
    "partner": {"id": 1},
    "product": {"id": 2},
    "sale_order": {"id": 3},
    "invoice": {"id": 4},
    "stock_item": {"id": 5},
    "manufacturing_order": {"id": 6},
}


def _passed_mapping(db, object_type="partner"):
    connection = _passed_connection_test(db, session_id=f"csess_ev_{object_type}")
    return _map(
        db,
        connection.connection_test_id,
        object_type=object_type,
        lookup=LOOKUPS[object_type],
        allow=True,
        client=MockOdooReadClient({object_type: PAYLOADS[object_type]}),
    )


def _create_pack(db, read_mapping_id, created_by="operator_1"):
    return OdooReadEvidencePackService(db).create_pack(
        OdooReadEvidencePackInput(read_mapping_id=read_mapping_id, created_by=created_by)
    )


@pytest.mark.parametrize(
    "object_type",
    ["partner", "product", "sale_order", "invoice", "stock_item", "manufacturing_order"],
)
def test_creates_evidence_pack_from_passed_mapping(db, object_type):
    mapping = _passed_mapping(db, object_type)

    result = _create_pack(db, mapping.read_mapping_id)

    assert result.evidence_pack_id.startswith("odoo_ev_")
    assert result.status == "created"
    assert result.object_type == object_type
    assert result.canonical_object_snapshot == mapping.canonical_object
    assert result.source_snapshot_redacted == mapping.source_snapshot_redacted
    assert result.safety_summary["evidence_only"] is True
    assert result.safety_summary["read_client_called"] is False
    assert result.safety_summary["new_erp_read_performed"] is False
    assert result.safety_summary["new_external_http_performed"] is False


def test_blocks_missing_read_mapping(db):
    result = _create_pack(db, "odoo_map_missing")

    assert result.status == "blocked"
    assert "read_mapping_not_found" in result.blocking_reasons


def test_blocks_non_passed_read_mapping(db):
    connection = _passed_connection_test(db, session_id="csess_ev_blocked")
    mapping = _map(
        db,
        connection.connection_test_id,
        object_type="partner",
        lookup={"id": 1},
        allow=False,
        client=MockOdooReadClient({"partner": PAYLOADS["partner"]}),
    )

    result = _create_pack(db, mapping.read_mapping_id)

    assert result.status == "blocked"
    assert "read_mapping_not_passed" in result.blocking_reasons


def test_blocks_missing_canonical_object(db):
    mapping = _passed_mapping(db, "partner")
    row = get_odoo_read_mapping_by_id(db, mapping.read_mapping_id)
    row.canonical_object_json = "{}"
    db.commit()

    result = _create_pack(db, mapping.read_mapping_id)

    assert result.status == "blocked"
    assert "canonical_object_missing" in result.blocking_reasons


def test_blocks_missing_source_snapshot_redaction(db):
    mapping = _passed_mapping(db, "partner")
    row = get_odoo_read_mapping_by_id(db, mapping.read_mapping_id)
    row.source_snapshot_redacted_json = "{}"
    db.commit()

    result = _create_pack(db, mapping.read_mapping_id)

    assert result.status == "blocked"
    assert "source_snapshot_redaction_missing" in result.blocking_reasons


def test_blocks_raw_secret_marker_in_unredacted_snapshot(db):
    mapping = _passed_mapping(db, "partner")
    row = get_odoo_read_mapping_by_id(db, mapping.read_mapping_id)
    row.source_snapshot_redacted_json = json.dumps(
        {"id": 1, "display_name": "Acme", "password": "plain-text"}
    )
    db.commit()

    result = _create_pack(db, mapping.read_mapping_id)

    assert result.status == "blocked"
    assert "raw_secret_marker_detected" in result.blocking_reasons


def test_safety_flags_are_false_and_no_raw_secret_exposed(db):
    mapping = _passed_mapping(db, "invoice")

    result = _create_pack(db, mapping.read_mapping_id)

    assert result.safety_summary["odoo_write_performed"] is False
    assert result.safety_summary["schema_inspection_performed"] is False
    assert result.safety_summary["permission_inspection_performed"] is False
    assert result.safety_summary["credentials_exposed"] is False
    assert result.safety_summary["raw_secret_accessed"] is False
    assert result.raw_secret_accessed is False
    assert "secret" not in str(result.canonical_object_snapshot).lower()
