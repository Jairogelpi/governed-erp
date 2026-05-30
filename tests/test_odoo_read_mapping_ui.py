"""UI tests for Sprint 76 - Odoo read mapping demo section."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_odoo_read_mapping_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Odoo Read Mapping" in response.content
    assert b"Partner/Product/Sale Order" in response.content
    assert b"Sprint 76 reads only partner, product and sale order data" in response.content
    assert b"odooMapConnectionTestId" in response.content
    assert b"odooMapAllowBusinessRead" in response.content
    assert b"odooMapRun" in response.content
    assert b"odooMapAudit" in response.content


def test_ui_states_no_invoice_stock_mrp_or_writes_boundary():
    client = TestClient(app)

    response = client.get("/demo")

    assert b"does not read invoices, stock, MRP" in response.content
    assert b"arbitrary models/domains" in response.content
    assert b"perform writes" in response.content
