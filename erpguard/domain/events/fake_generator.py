from __future__ import annotations

from decimal import Decimal
from uuid import uuid5, NAMESPACE_URL

from erpguard.canonical.enums import ProductTracking, ProductType, SalesOrderState
from erpguard.canonical.objects import Company, Customer, FormulaLine, Product, SalesOrder, SalesOrderLine


def _fake_sales_order(*, object_key: str, formula_valid: bool) -> SalesOrder:
    company = Company(id="company_fake", native_id="fake_company_1", name="Fake ERP Company", currency="EUR")
    customer = Customer(id="customer_fake", native_id="fake_customer_1", name="Fake Customer")
    product = Product(
        id="product_mikado_100",
        native_id="fake_product_100",
        sku="MIKADO-100",
        name="Mikado 100 ML",
        type=ProductType.STOCKABLE,
        tracking=ProductTracking.LOT,
        capacity_ml=Decimal("100"),
    )
    formula_ml = Decimal("100") if formula_valid else Decimal("60")
    return SalesOrder(
        id=object_key,
        native_id=f"fake_{object_key}",
        reference=object_key.upper(),
        company=company,
        customer=customer,
        state=SalesOrderState.DRAFT,
        currency="EUR",
        total_amount=Decimal("25.00"),
        lines=[
            SalesOrderLine(
                id=f"{object_key}_line_1",
                native_id=f"fake_{object_key}_line_1",
                product=product,
                quantity=Decimal("1"),
                unit_price=Decimal("25.00"),
                subtotal=Decimal("25.00"),
                formula_lines=[FormulaLine(component_name="Alcohol", ml=formula_ml)],
            )
        ],
    )


def build_fake_quote_to_order_ocel(*, tenant_id: str, object_key: str, formula_valid: bool) -> dict:
    """Fixture for historical replay (Phase 12): a `quotation`/`sales_order`
    object with a real `SalesOrder` state attached to it (as `ocel:ovmap`),
    plus `sales.quote.created`/`sales.quote.reviewed` events -- enough to
    exercise `evaluate_formula_guard_policy` via the replay engine, either
    passing (`formula_valid=True`) or blocked (`formula_valid=False`).
    """

    sales_order = _fake_sales_order(object_key=object_key, formula_valid=formula_valid)
    return {
        "ocel:global-event": {"ocel:activity": "erpguard.fake.quote_to_order", "ocel:version": "2.0"},
        "ocel:objects": {
            object_key: {"ocel:type": "sale_order", "ocel:ovmap": sales_order.model_dump(mode="json")},
        },
        "ocel:events": {
            f"{object_key}-created": {
                "ocel:activity": "sales.quote.created", "ocel:timestamp": "2026-01-01T00:00:00Z",
                "ocel:omap": [object_key], "ocel:vmap": {},
            },
            f"{object_key}-reviewed": {
                "ocel:activity": "sales.quote.reviewed", "ocel:timestamp": "2026-01-01T00:01:00Z",
                "ocel:omap": [object_key], "ocel:vmap": {},
            },
        },
    }


def build_fake_ocel(*, tenant_id: str) -> dict:
    seed = uuid5(NAMESPACE_URL, f"erpguard.fake:{tenant_id}").hex[:10]
    return {
        "ocel:global-event": {"ocel:activity": "erpguard.fake", "ocel:version": "2.0"},
        "ocel:objects": {
            f"fake-order-{seed}": {"ocel:type": "sale_order", "ocel:ovmap": {"name": "SO-FAKE"}},
            f"fake-customer-{seed}": {"ocel:type": "customer", "ocel:ovmap": {"name": "Fake Customer"}},
        },
        "ocel:events": {
            f"fake-created-{seed}": {
                "ocel:activity": "sales.order.created", "ocel:timestamp": "2026-01-01T00:00:00Z",
                "ocel:omap": [f"fake-order-{seed}", f"fake-customer-{seed}"], "ocel:vmap": {},
            },
            f"fake-reviewed-{seed}": {
                "ocel:activity": "sales.order.reviewed", "ocel:timestamp": "2026-01-01T00:01:00Z",
                "ocel:omap": [f"fake-order-{seed}"], "ocel:vmap": {},
            },
        },
    }
