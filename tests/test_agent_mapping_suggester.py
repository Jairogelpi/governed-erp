from __future__ import annotations

from erpguard.product.agent_mapping_suggester import suggest_mappings


def test_sales_order_fields_suggested():
    result = suggest_mappings("sales_order")
    assert result.target_entity == "sales_order"
    assert result.odoo_model == "sale.order"
    field_names = [f.field for f in result.suggested_fields]
    assert "name" in field_names
    assert "partner_id" in field_names


def test_invoice_fields_suggested():
    result = suggest_mappings("invoice")
    assert result.odoo_model == "account.move"
    field_names = [f.field for f in result.suggested_fields]
    assert "name" in field_names


def test_partner_fields_suggested():
    result = suggest_mappings("partner")
    assert result.odoo_model == "res.partner"
    assert any(f.required for f in result.suggested_fields)


def test_unknown_entity_returns_empty():
    result = suggest_mappings("unicorn")
    assert result.suggested_fields == []
    assert result.odoo_model == ""


def test_advisory_note_present():
    result = suggest_mappings("product")
    assert "Advisory only" in result.note
