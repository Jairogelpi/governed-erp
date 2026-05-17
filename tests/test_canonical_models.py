from decimal import Decimal

import pytest
from pydantic import ValidationError

from erpguard.canonical.actions import CANONICAL_ACTIONS, CanonicalActionDefinition
from erpguard.canonical.enums import (
    CanonicalAction,
    ERPType,
    InvariantSeverity,
    InvariantStatus,
    PreflightDecision,
    ProductTracking,
    ProductType,
    RiskLevel,
    SalesOrderState,
)
from erpguard.canonical.objects import (
    Company,
    Customer,
    FormulaLine,
    FormulaValidationSummary,
    Product,
    SalesOrder,
    SalesOrderLine,
)


def make_company() -> Company:
    return Company(id="company_1", native_id="1", name="Esenssi", currency="EUR")


def make_customer() -> Customer:
    return Customer(id="customer_1", native_id="10", name="Acme", active=True)


def make_product(**overrides) -> Product:
    data = {
        "id": "product_1",
        "native_id": "100",
        "name": "Mikado 100 ML",
        "active": True,
        "type": ProductType.STOCKABLE,
        "tracking": ProductTracking.LOT,
        "capacity_ml": Decimal("100"),
    }
    data.update(overrides)
    return Product(**data)


def make_line(**overrides) -> SalesOrderLine:
    data = {
        "id": "line_1",
        "native_id": "200",
        "product": make_product(),
        "quantity": Decimal("2"),
        "unit_price": Decimal("12.50"),
        "subtotal": Decimal("25.00"),
        "formula_lines": [
            FormulaLine(component_name="Alcohol", ml=Decimal("80")),
            FormulaLine(component_name="Fragrance", ml=Decimal("20")),
        ],
        "formula_validation": FormulaValidationSummary(
            required_ml_per_unit=Decimal("100"),
            actual_ml_per_unit=Decimal("100"),
            expected_total_ml=Decimal("200"),
            actual_total_ml=Decimal("200"),
            is_valid=True,
        ),
    }
    data.update(overrides)
    return SalesOrderLine(**data)


def test_valid_sales_order_object_serializes_to_json_and_dict():
    sales_order = SalesOrder(
        id="so_1",
        native_id="40",
        reference="S00040",
        company=make_company(),
        customer=make_customer(),
        state=SalesOrderState.DRAFT,
        currency="EUR",
        total_amount=Decimal("25.00"),
        lines=[make_line()],
    )

    dumped = sales_order.model_dump(mode="json")
    payload = sales_order.model_dump_json()

    assert dumped["state"] == "draft"
    assert dumped["lines"][0]["quantity"] == "2"
    assert '"reference":"S00040"' in payload


def test_sales_order_allows_empty_lines_for_raw_mapping():
    sales_order = SalesOrder(
        id="so_empty",
        native_id="41",
        reference="S00041",
        company=make_company(),
        customer=make_customer(),
        state=SalesOrderState.DRAFT,
        total_amount=Decimal("0"),
        lines=[],
    )

    assert sales_order.lines == []


def test_product_tracking_accepts_lot_serial_and_none():
    assert make_product(tracking=ProductTracking.LOT).tracking is ProductTracking.LOT
    assert make_product(tracking=ProductTracking.SERIAL).tracking is ProductTracking.SERIAL
    assert make_product(tracking=ProductTracking.NONE).tracking is ProductTracking.NONE


def test_negative_quantity_is_invalid():
    with pytest.raises(ValidationError):
        make_line(quantity=Decimal("-1"))


def test_negative_product_capacity_is_invalid():
    with pytest.raises(ValidationError):
        make_product(capacity_ml=Decimal("-1"))


def test_negative_formula_ml_is_invalid():
    with pytest.raises(ValidationError):
        FormulaLine(component_name="Alcohol", ml=Decimal("-0.01"))


def test_canonical_action_enum_values_and_definitions():
    assert ERPType.ODOO.value == "odoo"
    assert CanonicalAction.CONFIRM_SALES_ORDER.value == "confirm_sales_order"
    assert CanonicalAction.INSPECT_SALES_ORDER.value == "inspect_sales_order"
    assert CanonicalAction.VALIDATE_FORMULA.value == "validate_formula"
    assert CanonicalAction.INSPECT_ACCESS_RULES.value == "inspect_access_rules"
    assert RiskLevel.R3.value == "R3"
    assert PreflightDecision.BLOCK.value == "block"
    assert InvariantSeverity.BLOCKING.value == "blocking"
    assert InvariantStatus.PASSED.value == "passed"

    definition = CANONICAL_ACTIONS[CanonicalAction.CONFIRM_SALES_ORDER]

    assert isinstance(definition, CanonicalActionDefinition)
    assert definition.name == CanonicalAction.CONFIRM_SALES_ORDER
    assert definition.default_risk_level is RiskLevel.R3
