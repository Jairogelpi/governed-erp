"""UI tests for Sprint 76/77 - Odoo read mapping demo section."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_odoo_read_mapping_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Odoo Read Mapping" in response.content
    assert b"Business Objects" in response.content
    assert b"Sprint 77 supports partner, product, sale_order, invoice, stock_item and manufacturing_order" in response.content
    assert b"odooMapConnectionTestId" in response.content
    assert b"odooMapAllowBusinessRead" in response.content
    assert b"odooMapRun" in response.content
    assert b"odooMapAudit" in response.content


def test_ui_states_no_writes_boundary():
    client = TestClient(app)

    response = client.get("/demo")

    assert b"does not post invoices" in response.content
    assert b"move stock" in response.content
    assert b"perform writes" in response.content
