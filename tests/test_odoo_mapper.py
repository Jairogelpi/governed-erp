from decimal import Decimal

from erpguard.adapters.odoo.mapper import map_odoo_sale_order_to_canonical
from erpguard.canonical.enums import ProductTracking, ProductType, SalesOrderState


def sale_order_payload() -> dict:
    return {
        "id": 40,
        "name": "S00040",
        "state": "draft",
        "currency_id": [1, "EUR"],
        "amount_total": 250.0,
        "amount_untaxed": 200.0,
        "amount_tax": 50.0,
        "partner_id": [10, "ACME Customer"],
        "company_id": [1, "Esenssi"],
        "order_line": [101],
    }


def line_payloads() -> list[dict]:
    return [
        {
            "id": 101,
            "order_id": [40, "S00040"],
            "product_id": [1001, "Mikado 100 ML"],
            "product_uom_qty": 2.0,
            "product_uom": [1, "Units"],
            "price_unit": 125.0,
            "price_subtotal": 250.0,
            "tax_id": [5],
        }
    ]


def product_payloads() -> list[dict]:
    return [
        {
            "id": 1001,
            "default_code": "MIKADO-100",
            "display_name": "Mikado 100 ML",
            "active": True,
            "detailed_type": "product",
            "tracking": "lot",
            "categ_id": [3, "Finished Goods"],
            "standard_price": 40.0,
            "lst_price": 125.0,
            "uom_id": [1, "Units"],
            "x_capacity_ml": 100.0,
        }
    ]


def formula_payloads() -> list[dict]:
    return [
        {
            "id": 5001,
            "sale_order_line_id": [101, "S00040 - Mikado"],
            "fragrance_id": [7001, "Amber"],
            "component_name": "Amber",
            "ml_per_unit": 100.0,
            "ml_total": 200.0,
        }
    ]


def test_maps_odoo_sale_order_to_canonical_sales_order():
    order = map_odoo_sale_order_to_canonical(
        sale_order_payload(),
        line_payloads(),
        product_payloads(),
    )

    assert order.id == "odoo:sale.order:40"
    assert order.native_id == "40"
    assert order.reference == "S00040"
    assert order.state is SalesOrderState.DRAFT
    assert order.currency == "EUR"
    assert order.customer is not None
    assert order.customer.name == "ACME Customer"
    assert order.company is not None
    assert order.company.name == "Esenssi"
    assert len(order.lines) == 1
    assert order.lines[0].quantity == Decimal("2.0")


def test_maps_odoo_product_fields_including_capacity_and_tracking():
    order = map_odoo_sale_order_to_canonical(
        sale_order_payload(),
        line_payloads(),
        product_payloads(),
    )

    product = order.lines[0].product

    assert product.id == "odoo:product.product:1001"
    assert product.sku == "MIKADO-100"
    assert product.type is ProductType.STOCKABLE
    assert product.tracking is ProductTracking.LOT
    assert product.capacity_ml == Decimal("100.0")


def test_maps_optional_formula_payloads():
    order = map_odoo_sale_order_to_canonical(
        sale_order_payload(),
        line_payloads(),
        product_payloads(),
        formula_payloads=formula_payloads(),
    )

    formula = order.lines[0].formula_lines[0]

    assert formula.id == "odoo:formula:5001"
    assert formula.sales_order_line_id == "odoo:sale.order.line:101"
    assert formula.fragrance_id == "7001"
    assert formula.component_name == "Amber"
    assert formula.ml_per_unit == Decimal("100.0")
    assert formula.ml_total == Decimal("200.0")
