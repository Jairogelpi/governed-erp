"""Tests for Sprint 79 - Odoo read-only demo flow."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.product.odoo_read_only_demo_flow import (
    OdooReadOnlyDemoFlowInput,
    OdooReadOnlyDemoFlowService,
)
from test_odoo_connection_test import MockOdooConnectionClient
from test_odoo_read_mapping import MockOdooReadClient
from test_odoo_read_only_adapter_shell import _activation


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


DEMO_PAYLOADS = {
    "partner": {"id": 1, "display_name": "Acme"},
    "product": {"id": 2, "display_name": "Kit"},
    "sale_order": {"id": 3, "name": "S00001"},
    "invoice": {"id": 4, "name": "INV/2026/001"},
    "stock_item": {"id": 5, "display_name": "WH/Stock - SKU"},
    "manufacturing_order": {"id": 6, "name": "MO/2026/001"},
}


def _service(db, *, read_client=None, connection_client=None):
    return OdooReadOnlyDemoFlowService(
        db,
        connection_client=connection_client or MockOdooConnectionClient(succeeds=True),
        read_client=read_client or MockOdooReadClient(DEMO_PAYLOADS),
    )


def _run(db, activation_id, **kwargs):
    return _service(db).run_flow(
        OdooReadOnlyDemoFlowInput(
            activation_id=activation_id,
            requested_by=kwargs.get("requested_by", "operator_1"),
            object_types=kwargs.get("object_types"),
            allow_network_test=kwargs.get("allow_network_test", True),
            allow_business_read=kwargs.get("allow_business_read", True),
        )
    )


def test_creates_demo_flow_from_active_read_only_activation(db):
    activation = _activation(db)

    result = _run(db, activation.activation_id)

    assert result.demo_flow_id.startswith("odoo_demo_")
    assert result.status == "completed"
    assert result.adapter_session_id.startswith("odoo_ro_")
    assert result.connection_test_id.startswith("odoo_ct_")
    assert len(result.read_mapping_ids) == 3
    assert len(result.evidence_pack_ids) == 3


def test_default_object_types_are_partner_product_sale_order(db):
    activation = _activation(db)

    result = _run(db, activation.activation_id, object_types=None)

    assert result.requested_object_types == ["partner", "product", "sale_order"]
    assert [summary["object_type"] for summary in result.object_summaries] == [
        "partner",
        "product",
        "sale_order",
    ]


def test_blocks_when_network_test_not_allowed(db):
    activation = _activation(db)

    result = _run(db, activation.activation_id, allow_network_test=False)

    assert result.status == "blocked"
    assert "network_test_not_allowed" in result.blocking_reasons
    assert result.connection_test_id == ""
    assert result.read_mapping_ids == []


def test_blocks_when_business_read_not_allowed(db):
    activation = _activation(db)

    result = _run(db, activation.activation_id, allow_business_read=False)

    assert result.status == "blocked"
    assert "business_read_not_allowed" in result.blocking_reasons
    assert result.connection_test_id.startswith("odoo_ct_")
    assert result.read_mapping_ids == []


@pytest.mark.parametrize("object_type", ["payment", "journal_entry", "stock_move", "purchase_order"])
def test_blocks_unsupported_objects(db, object_type):
    activation = _activation(db)

    result = _run(db, activation.activation_id, object_types=[object_type])

    assert result.status == "blocked"
    assert "unsupported_object_type" in result.blocking_reasons


def test_object_summaries_include_external_id_and_display_name(db):
    activation = _activation(db)

    result = _run(db, activation.activation_id, object_types=["invoice", "stock_item", "manufacturing_order"])

    assert result.status == "completed"
    assert [summary["object_type"] for summary in result.object_summaries] == [
        "invoice",
        "stock_item",
        "manufacturing_order",
    ]
    assert result.object_summaries[0]["external_id"] == "4"
    assert result.object_summaries[0]["display_name"] == "INV/2026/001"
    assert all(summary["read_mapping_id"].startswith("odoo_map_") for summary in result.object_summaries)
    assert all(summary["evidence_pack_id"].startswith("odoo_ev_") for summary in result.object_summaries)


def test_safety_summary_flags(db):
    activation = _activation(db)

    result = _run(db, activation.activation_id)

    assert result.safety_summary["demo_only"] is True
    assert result.safety_summary["odoo_write_performed"] is False
    assert result.safety_summary["write_preview_performed"] is False
    assert result.safety_summary["arbitrary_model_access"] is False
    assert result.safety_summary["arbitrary_domain_execution"] is False
    assert result.safety_summary["browser_control_performed"] is False
    assert result.safety_summary["mcp_execution_performed"] is False
    assert result.safety_summary["scheduler_used"] is False
    assert result.safety_summary["credentials_exposed"] is False
    assert result.safety_summary["raw_secret_accessed"] is False
