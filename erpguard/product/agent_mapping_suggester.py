from __future__ import annotations

from pydantic import BaseModel, Field


_ENTITY_FIELDS: dict[str, list[dict]] = {
    "sales_order": [
        {"field": "name", "odoo_field": "name", "description": "Order reference (e.g. SO042)", "required": True},
        {"field": "partner_id", "odoo_field": "partner_id", "description": "Customer", "required": True},
        {"field": "date_order", "odoo_field": "date_order", "description": "Order date", "required": False},
        {"field": "amount_total", "odoo_field": "amount_total", "description": "Total amount", "required": False},
        {"field": "state", "odoo_field": "state", "description": "Status (draft/sale/done/cancel)", "required": False},
    ],
    "invoice": [
        {"field": "name", "odoo_field": "name", "description": "Invoice number", "required": True},
        {"field": "partner_id", "odoo_field": "partner_id", "description": "Customer / vendor", "required": True},
        {"field": "invoice_date", "odoo_field": "invoice_date", "description": "Invoice date", "required": False},
        {"field": "amount_total", "odoo_field": "amount_total", "description": "Total amount", "required": False},
        {"field": "state", "odoo_field": "state", "description": "Status (draft/posted/paid)", "required": False},
    ],
    "partner": [
        {"field": "name", "odoo_field": "name", "description": "Partner name", "required": True},
        {"field": "email", "odoo_field": "email", "description": "Email address", "required": False},
        {"field": "phone", "odoo_field": "phone", "description": "Phone number", "required": False},
        {"field": "vat", "odoo_field": "vat", "description": "VAT / Tax ID", "required": False},
    ],
    "product": [
        {"field": "name", "odoo_field": "name", "description": "Product name", "required": True},
        {"field": "default_code", "odoo_field": "default_code", "description": "Internal reference / SKU", "required": False},
        {"field": "list_price", "odoo_field": "list_price", "description": "Sales price", "required": False},
        {"field": "qty_available", "odoo_field": "qty_available", "description": "Available quantity", "required": False},
    ],
    "purchase_order": [
        {"field": "name", "odoo_field": "name", "description": "PO reference (e.g. PO042)", "required": True},
        {"field": "partner_id", "odoo_field": "partner_id", "description": "Vendor", "required": True},
        {"field": "date_order", "odoo_field": "date_order", "description": "Order date", "required": False},
        {"field": "amount_total", "odoo_field": "amount_total", "description": "Total amount", "required": False},
    ],
    "inventory": [
        {"field": "product_id", "odoo_field": "product_id", "description": "Product", "required": True},
        {"field": "location_id", "odoo_field": "location_id", "description": "Warehouse location", "required": True},
        {"field": "qty_available", "odoo_field": "qty_available", "description": "Available quantity", "required": False},
    ],
    "payment": [
        {"field": "partner_id", "odoo_field": "partner_id", "description": "Customer / vendor", "required": True},
        {"field": "amount", "odoo_field": "amount", "description": "Payment amount", "required": True},
        {"field": "date", "odoo_field": "date", "description": "Payment date", "required": False},
        {"field": "journal_id", "odoo_field": "journal_id", "description": "Journal (bank/cash)", "required": False},
    ],
}

_ODOO_MODELS: dict[str, str] = {
    "sales_order": "sale.order",
    "invoice": "account.move",
    "partner": "res.partner",
    "product": "product.template",
    "purchase_order": "purchase.order",
    "inventory": "stock.quant",
    "payment": "account.payment",
}


class EntityMappingSuggestion(BaseModel):
    field: str
    odoo_field: str
    description: str
    required: bool = False


class EntityMappingsResult(BaseModel):
    target_entity: str
    odoo_model: str = ""
    suggested_fields: list[EntityMappingSuggestion] = Field(default_factory=list)
    note: str = (
        "Advisory only. Field suggestions are based on standard Odoo models. "
        "Verify against your specific installation."
    )


def suggest_mappings(target_entity: str) -> EntityMappingsResult:
    fields = _ENTITY_FIELDS.get(target_entity, [])
    return EntityMappingsResult(
        target_entity=target_entity,
        odoo_model=_ODOO_MODELS.get(target_entity, ""),
        suggested_fields=[EntityMappingSuggestion(**f) for f in fields],
    )
