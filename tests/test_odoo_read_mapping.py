"""Tests for Sprint 76/77 - controlled Odoo read mapping."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.models import Base
from erpguard.db.repositories import get_odoo_connection_test_by_id
from erpguard.product.connector_credential_vault import CredentialVaultContractService
from erpguard.product.odoo_connection_test import (
    OdooConnectionTestInput,
    OdooConnectionTestService,
)
from erpguard.product.odoo_read_mapping import (
    OdooReadMappingInput,
    OdooReadMappingService,
)
from test_odoo_connection_test import MockOdooConnectionClient, _adapter_session


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


class MockOdooReadClient:
    def __init__(self, payload_by_object=None, *, fails=False):
        self.payload_by_object = payload_by_object or {}
        self.fails = fails
        self.calls = []

    def read_allowed_object(self, *, object_type, lookup, field_allowlist):
        self.calls.append(
            {
                "object_type": object_type,
                "lookup": lookup,
                "field_allowlist": list(field_allowlist),
            }
        )
        if self.fails:
            raise RuntimeError("mock read failed")
        return self.payload_by_object.get(object_type, {})


def _passed_connection_test(db, *, session_id="csess_odoo_map", secret="odoo-map-secret"):
    adapter_session = _adapter_session(db, session_id=session_id, secret=secret)
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


def _map(db, connection_test_id, *, object_type="sale_order", lookup=None, allow=False, client=None):
    return OdooReadMappingService(db, read_client=client).run_mapping(
        OdooReadMappingInput(
            connection_test_id=connection_test_id,
            requested_by="operator_1",
            object_type=object_type,
            lookup=lookup if lookup is not None else {"reference": "S00001"},
            allow_business_read=allow,
        )
    )


def test_blocks_by_default_without_calling_read_client(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient()

    result = _map(db, connection.connection_test_id, allow=False, client=client)

    assert result.status == "blocked"
    assert "business_read_not_allowed" in result.blocking_reasons
    assert result.business_data_read is False
    assert client.calls == []


def test_blocks_missing_connection_test(db):
    result = _map(db, "odoo_ct_missing", allow=True, client=MockOdooReadClient())

    assert result.status == "blocked"
    assert "connection_test_not_found" in result.blocking_reasons


def test_blocks_non_passed_connection_test(db):
    adapter_session = _adapter_session(db, session_id="csess_odoo_map_blocked")
    blocked = OdooConnectionTestService(db).run_test(
        OdooConnectionTestInput(adapter_session_id=adapter_session.adapter_session_id)
    )

    result = _map(db, blocked.connection_test_id, allow=True, client=MockOdooReadClient())

    assert result.status == "blocked"
    assert "connection_test_not_passed" in result.blocking_reasons


@pytest.mark.parametrize("object_type", ["payment", "journal_entry", "stock_move", "purchase_order"])
def test_blocks_unsupported_object_types(db, object_type):
    connection = _passed_connection_test(db, session_id=f"csess_odoo_map_{object_type}")

    result = _map(
        db,
        connection.connection_test_id,
        object_type=object_type,
        lookup={"id": 1},
        allow=True,
        client=MockOdooReadClient(),
    )

    assert result.status == "blocked"
    assert "object_type_not_allowed" in result.blocking_reasons


@pytest.mark.parametrize(
    ("object_type", "lookup"),
    [
        ("invoice", {"email": "not-supported@example.com"}),
        ("stock_item", {"name": "not-supported"}),
        ("manufacturing_order", {"product_code": "not-supported"}),
    ],
)
def test_blocks_unsupported_sprint_77_lookup_keys(db, object_type, lookup):
    connection = _passed_connection_test(db, session_id=f"csess_odoo_map_lookup_{object_type}")

    result = _map(
        db,
        connection.connection_test_id,
        object_type=object_type,
        lookup=lookup,
        allow=True,
        client=MockOdooReadClient(),
    )

    assert result.status == "blocked"
    assert "lookup_not_supported" in result.blocking_reasons


def test_blocks_missing_lookup(db):
    connection = _passed_connection_test(db)

    result = _map(db, connection.connection_test_id, lookup={}, allow=True, client=MockOdooReadClient())

    assert result.status == "blocked"
    assert "lookup_missing" in result.blocking_reasons


def test_blocks_unsupported_lookup_key(db):
    connection = _passed_connection_test(db)

    result = _map(
        db,
        connection.connection_test_id,
        object_type="partner",
        lookup={"domain": [["name", "ilike", "Acme"]]},
        allow=True,
        client=MockOdooReadClient(),
    )

    assert result.status == "blocked"
    assert "lookup_not_supported" in result.blocking_reasons


def test_blocks_credential_not_found(db):
    connection = _passed_connection_test(db)
    row = get_odoo_connection_test_by_id(db, connection.connection_test_id)
    row.credential_ref = "cred_missing"
    db.commit()

    result = _map(db, connection.connection_test_id, allow=True, client=MockOdooReadClient())

    assert result.status == "blocked"
    assert "credential_not_found" in result.blocking_reasons


def test_blocks_credential_revoked(db):
    connection = _passed_connection_test(db)
    CredentialVaultContractService(db).revoke_credential(
        connection.credential_ref, revoked_by="operator_1"
    )

    result = _map(db, connection.connection_test_id, allow=True, client=MockOdooReadClient())

    assert result.status == "blocked"
    assert "credential_revoked" in result.blocking_reasons


def test_maps_partner_to_canonical_partner_and_redacts_extra_fields(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient(
        {
            "partner": {
                "id": 7,
                "display_name": "Acme SL",
                "email": "hello@acme.example",
                "phone": "+34 600 000 000",
                "password": "must-not-leak",
            }
        }
    )

    result = _map(
        db,
        connection.connection_test_id,
        object_type="partner",
        lookup={"email": "hello@acme.example"},
        allow=True,
        client=client,
    )

    assert result.status == "passed"
    assert result.canonical_object["object_type"] == "partner"
    assert result.canonical_object["external_id"] == "7"
    assert result.canonical_object["display_name"] == "Acme SL"
    assert result.canonical_object["source_model_hint"] == "res.partner"
    assert result.source_snapshot_redacted["password"] == "<redacted>"
    assert "password" not in result.field_allowlist_used


def test_maps_product_to_canonical_product(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient(
        {
            "product": {
                "id": 42,
                "display_name": "Starter Kit",
                "default_code": "KIT-001",
                "sale_ok": True,
                "purchase_ok": False,
            }
        }
    )

    result = _map(
        db,
        connection.connection_test_id,
        object_type="product",
        lookup={"default_code": "KIT-001"},
        allow=True,
        client=client,
    )

    assert result.status == "passed"
    assert result.canonical_object["object_type"] == "product"
    assert result.canonical_object["external_id"] == "42"
    assert result.canonical_object["default_code"] == "KIT-001"
    assert result.canonical_object["source_model_hint"] == "product.template/product.product"


def test_maps_sale_order_to_canonical_sale_order(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient(
        {
            "sale_order": {
                "id": 101,
                "name": "S00001",
                "partner_id": [7, "Acme SL"],
                "state": "sale",
                "amount_total": 123.45,
                "currency_id": [1, "EUR"],
                "date_order": "2026-05-30",
                "order_line": [1, 2, 3],
            }
        }
    )

    result = _map(
        db,
        connection.connection_test_id,
        object_type="sale_order",
        lookup={"reference": "S00001"},
        allow=True,
        client=client,
    )

    assert result.status == "passed"
    assert result.canonical_object["object_type"] == "sale_order"
    assert result.canonical_object["external_id"] == "101"
    assert result.canonical_object["display_name"] == "S00001"
    assert result.canonical_object["partner_ref"] == "7"
    assert result.canonical_object["line_count"] == 3
    assert result.canonical_object["source_model_hint"] == "sale.order"


def test_maps_invoice_to_canonical_invoice_and_redacts_extra_fields(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient(
        {
            "invoice": {
                "id": 301,
                "name": "INV/2026/001",
                "ref": "INV/2026/001",
                "partner_id": [7, "Acme SL"],
                "state": "posted",
                "move_type": "out_invoice",
                "amount_total": 240.0,
                "amount_residual": 40.0,
                "currency_id": [1, "EUR"],
                "invoice_date": "2026-05-30",
                "payment_token": "must-not-leak",
            }
        }
    )

    result = _map(
        db,
        connection.connection_test_id,
        object_type="invoice",
        lookup={"reference": "INV/2026/001"},
        allow=True,
        client=client,
    )

    assert result.status == "passed"
    assert result.canonical_object["object_type"] == "invoice"
    assert result.canonical_object["external_id"] == "301"
    assert result.canonical_object["display_name"] == "INV/2026/001"
    assert result.canonical_object["partner_ref"] == "7"
    assert result.canonical_object["move_type"] == "out_invoice"
    assert result.canonical_object["amount_residual"] == 40.0
    assert result.canonical_object["currency"] == "1"
    assert result.canonical_object["invoice_date"] == "2026-05-30"
    assert result.canonical_object["source_model_hint"] == "account.move"
    assert result.source_snapshot_redacted["payment_token"] == "<redacted>"


def test_maps_stock_item_to_canonical_stock_item_and_redacts_extra_fields(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient(
        {
            "stock_item": {
                "id": 88,
                "display_name": "WH/Stock - SKU-001",
                "product_id": [42, "SKU-001"],
                "location_id": [3, "WH/Stock"],
                "quantity": 12.5,
                "reserved_quantity": 2.0,
                "cost_secret": "must-not-leak",
            }
        }
    )

    result = _map(
        db,
        connection.connection_test_id,
        object_type="stock_item",
        lookup={"product_code": "SKU-001"},
        allow=True,
        client=client,
    )

    assert result.status == "passed"
    assert result.canonical_object["object_type"] == "stock_item"
    assert result.canonical_object["external_id"] == "88"
    assert result.canonical_object["display_name"] == "WH/Stock - SKU-001"
    assert result.canonical_object["product_ref"] == "42"
    assert result.canonical_object["location_ref"] == "3"
    assert result.canonical_object["quantity"] == 12.5
    assert result.canonical_object["reserved_quantity"] == 2.0
    assert result.canonical_object["source_model_hint"] == "stock.quant"
    assert result.source_snapshot_redacted["cost_secret"] == "<redacted>"


def test_maps_manufacturing_order_to_canonical_manufacturing_order_and_redacts_extra_fields(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient(
        {
            "manufacturing_order": {
                "id": 500,
                "name": "MO/2026/001",
                "product_id": [42, "SKU-001"],
                "state": "confirmed",
                "product_qty": 10.0,
                "qty_produced": 4.0,
                "bom_id": [11, "BOM/SKU-001"],
                "workorder_token": "must-not-leak",
            }
        }
    )

    result = _map(
        db,
        connection.connection_test_id,
        object_type="manufacturing_order",
        lookup={"reference": "MO/2026/001"},
        allow=True,
        client=client,
    )

    assert result.status == "passed"
    assert result.canonical_object["object_type"] == "manufacturing_order"
    assert result.canonical_object["external_id"] == "500"
    assert result.canonical_object["display_name"] == "MO/2026/001"
    assert result.canonical_object["product_ref"] == "42"
    assert result.canonical_object["state"] == "confirmed"
    assert result.canonical_object["product_qty"] == 10.0
    assert result.canonical_object["qty_produced"] == 4.0
    assert result.canonical_object["bom_ref"] == "11"
    assert result.canonical_object["source_model_hint"] == "mrp.production"
    assert result.source_snapshot_redacted["workorder_token"] == "<redacted>"


def test_read_client_used_only_when_business_read_allowed(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient({"partner": {"id": 1, "display_name": "A"}})

    _map(db, connection.connection_test_id, object_type="partner", lookup={"id": 1}, allow=False, client=client)
    _map(db, connection.connection_test_id, object_type="partner", lookup={"id": 1}, allow=True, client=client)

    assert len(client.calls) == 1
    assert client.calls[0]["object_type"] == "partner"
    assert "domain" not in client.calls[0]


def test_canonical_identity_missing_blocks(db):
    connection = _passed_connection_test(db)
    client = MockOdooReadClient({"partner": {"email": "missing-id@example.com"}})

    result = _map(
        db,
        connection.connection_test_id,
        object_type="partner",
        lookup={"email": "missing-id@example.com"},
        allow=True,
        client=client,
    )

    assert result.status == "failed"
    assert "canonical_identity_missing" in result.blocking_reasons


def test_read_client_failed_returns_failed(db):
    connection = _passed_connection_test(db)

    result = _map(
        db,
        connection.connection_test_id,
        object_type="product",
        lookup={"name": "Kit"},
        allow=True,
        client=MockOdooReadClient(fails=True),
    )

    assert result.status == "failed"
    assert "read_client_failed" in result.blocking_reasons


def test_safety_flags_and_public_response_do_not_expose_secret(db):
    connection = _passed_connection_test(db, secret="super-private-read-secret")
    client = MockOdooReadClient({"sale_order": {"id": 1, "name": "S00001"}})

    result = _map(db, connection.connection_test_id, allow=True, client=client)

    assert result.odoo_write_performed is False
    assert result.schema_inspection_performed is False
    assert result.permission_inspection_performed is False
    assert result.credentials_exposed is False
    assert result.raw_secret_accessed is False
    assert "super-private-read-secret" not in str(result.__dict__)
