from decimal import Decimal
from typing import Any

from erpguard.canonical.enums import ProductTracking, ProductType, SalesOrderState
from erpguard.canonical.objects import Company, Customer, FormulaLine, Product, SalesOrder, SalesOrderLine


def map_odoo_sale_order_to_canonical(
    order_payload: dict,
    line_payloads: list[dict],
    product_payloads: list[dict],
    formula_payloads: list[dict] | None = None,
) -> SalesOrder:
    product_by_id = {_native_id(product["id"]): _map_product(product) for product in product_payloads}
    formulas_by_line_id = _group_formulas_by_line_id(formula_payloads or [])
    lines = [
        _map_line(line, product_by_id, formulas_by_line_id.get(_native_id(line["id"]), []))
        for line in line_payloads
    ]

    return SalesOrder(
        id=f"odoo:sale.order:{order_payload['id']}",
        native_id=_native_id(order_payload["id"]),
        reference=order_payload.get("name", _native_id(order_payload["id"])),
        company=_map_company(order_payload.get("company_id")),
        customer=_map_customer(order_payload.get("partner_id")),
        state=_map_sales_order_state(order_payload.get("state")),
        currency=_many2one_name(order_payload.get("currency_id")),
        total_amount=_decimal(order_payload.get("amount_total", 0)),
        untaxed_amount=_decimal_or_none(order_payload.get("amount_untaxed")),
        tax_amount=_decimal_or_none(order_payload.get("amount_tax")),
        lines=lines,
        native_metadata={"odoo_model": "sale.order", "payload": order_payload},
    )


def _map_company(value) -> Company | None:
    if not value:
        return None
    native_id, name = _many2one_parts(value)
    return Company(id=f"odoo:res.company:{native_id}", native_id=native_id, name=name)


def _map_customer(value) -> Customer | None:
    if not value:
        return None
    native_id, name = _many2one_parts(value)
    return Customer(id=f"odoo:res.partner:{native_id}", native_id=native_id, name=name, active=True)


def _map_product(payload: dict) -> Product:
    native_id = _native_id(payload["id"])
    return Product(
        id=f"odoo:product.product:{native_id}",
        native_id=native_id,
        sku=payload.get("default_code"),
        name=payload.get("display_name") or payload.get("name") or native_id,
        active=payload.get("active", True),
        type=_map_product_type(payload.get("detailed_type") or payload.get("type")),
        tracking=_map_tracking(payload.get("tracking")),
        category=_many2one_name(payload.get("categ_id")),
        cost=_decimal_or_none(payload.get("standard_price")),
        sale_price=_decimal_or_none(payload.get("lst_price")),
        uom=_many2one_name(payload.get("uom_id")),
        capacity_ml=_decimal_or_none(payload.get("x_capacity_ml")),
        native_metadata={"odoo_model": "product.product", "payload": payload},
    )


def _map_line(line: dict, product_by_id: dict[str, Product], formula_lines: list[FormulaLine]) -> SalesOrderLine:
    native_id = _native_id(line["id"])
    product_native_id = _many2one_id(line.get("product_id"))
    product = product_by_id.get(product_native_id) or Product(
        id=f"odoo:product.product:{product_native_id}",
        native_id=product_native_id,
        name=_many2one_name(line.get("product_id")) or product_native_id,
    )
    return SalesOrderLine(
        id=f"odoo:sale.order.line:{native_id}",
        native_id=native_id,
        product=product,
        quantity=_decimal(line.get("product_uom_qty", 0)),
        uom=_many2one_name(line.get("product_uom")),
        unit_price=_decimal(line.get("price_unit", 0)),
        subtotal=_decimal(line.get("price_subtotal", 0)),
        tax_ids=[str(value) for value in line.get("tax_id", [])],
        formula_lines=formula_lines,
        native_metadata={"odoo_model": "sale.order.line", "payload": line},
    )


def _group_formulas_by_line_id(payloads: list[dict]) -> dict[str, list[FormulaLine]]:
    grouped: dict[str, list[FormulaLine]] = {}
    for payload in payloads:
        line_id = _many2one_id(payload.get("sale_order_line_id"))
        grouped.setdefault(line_id, []).append(_map_formula(payload, line_id))
    return grouped


def _map_formula(payload: dict, line_native_id: str) -> FormulaLine:
    native_id = _native_id(payload["id"])
    return FormulaLine(
        id=f"odoo:formula:{native_id}",
        sales_order_line_id=f"odoo:sale.order.line:{line_native_id}",
        fragrance_id=_many2one_id(payload.get("fragrance_id")),
        component_name=payload.get("component_name") or _many2one_name(payload.get("fragrance_id")) or "",
        ml_per_unit=_decimal_or_none(payload.get("ml_per_unit")),
        ml_total=_decimal_or_none(payload.get("ml_total")),
        ml=_decimal(payload.get("ml_per_unit", payload.get("ml", 0))),
        native_metadata={"odoo_model": "formula", "payload": payload},
    )


def _map_sales_order_state(value: str | None) -> SalesOrderState:
    mapping = {
        "draft": SalesOrderState.DRAFT,
        "sent": SalesOrderState.SENT,
        "sale": SalesOrderState.CONFIRMED,
        "done": SalesOrderState.DONE,
        "cancel": SalesOrderState.CANCELLED,
    }
    return mapping.get(value or "", SalesOrderState.UNKNOWN)


def _map_product_type(value: str | None) -> ProductType:
    mapping = {
        "product": ProductType.STOCKABLE,
        "consu": ProductType.CONSUMABLE,
        "service": ProductType.SERVICE,
    }
    return mapping.get(value or "", ProductType.UNKNOWN)


def _map_tracking(value: str | None) -> ProductTracking:
    mapping = {
        "none": ProductTracking.NONE,
        "lot": ProductTracking.LOT,
        "serial": ProductTracking.SERIAL,
    }
    return mapping.get(value or "", ProductTracking.UNKNOWN)


def _many2one_parts(value: Any) -> tuple[str, str]:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return _native_id(value[0]), str(value[1])
    return _native_id(value), str(value)


def _many2one_id(value: Any) -> str:
    if isinstance(value, (list, tuple)) and value:
        return _native_id(value[0])
    return _native_id(value)


def _many2one_name(value: Any) -> str | None:
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        return str(value[1])
    return None


def _native_id(value: Any) -> str:
    return str(value)


def _decimal(value: Any) -> Decimal:
    return Decimal(str(value))


def _decimal_or_none(value: Any) -> Decimal | None:
    if value is None or value is False:
        return None
    return _decimal(value)
