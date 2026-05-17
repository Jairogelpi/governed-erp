from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from erpguard.canonical.enums import ProductTracking, ProductType, SalesOrderState


class CanonicalModel(BaseModel):
    model_config = ConfigDict(
        use_enum_values=False,
    )


class Company(CanonicalModel):
    id: str
    native_id: str
    name: str
    currency: str | None = None
    native_metadata: dict[str, Any] = Field(default_factory=dict)


class Customer(CanonicalModel):
    id: str
    native_id: str
    name: str
    email: str | None = None
    active: bool = True
    native_metadata: dict[str, Any] = Field(default_factory=dict)


class FormulaLine(CanonicalModel):
    component_name: str = ""
    ml: Decimal = Field(default=Decimal("0"), ge=0)
    id: str | None = None
    sales_order_line_id: str | None = None
    fragrance_id: str | None = None
    ml_per_unit: Decimal | None = Field(default=None, ge=0)
    ml_total: Decimal | None = Field(default=None, ge=0)
    product_native_id: str | None = None
    native_metadata: dict[str, Any] = Field(default_factory=dict)


class FormulaValidationError(CanonicalModel):
    code: str
    line_id: str | None = None
    product_name: str | None = None
    expected_ml: Decimal | None = Field(default=None, ge=0)
    actual_ml: Decimal | None = Field(default=None, ge=0)
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class FormulaValidationSummary(CanonicalModel):
    required_ml_per_unit: Decimal | None = Field(default=None, ge=0)
    actual_ml_per_unit: Decimal | None = Field(default=None, ge=0)
    expected_total_ml: Decimal | None = Field(default=None, ge=0)
    actual_total_ml: Decimal | None = Field(default=None, ge=0)
    is_valid: bool = True
    checked_lines_count: int = Field(default=0, ge=0)
    skipped_lines_count: int = Field(default=0, ge=0)
    error_count: int = Field(default=0, ge=0)
    errors: list[FormulaValidationError] = Field(default_factory=list)
    warnings: list[FormulaValidationError] = Field(default_factory=list)
    message: str | None = None
    evidence: dict[str, Any] = Field(default_factory=dict)


class Product(CanonicalModel):
    id: str
    native_id: str
    name: str
    sku: str | None = None
    active: bool = True
    type: ProductType = ProductType.UNKNOWN
    tracking: ProductTracking = ProductTracking.UNKNOWN
    category: str | None = None
    cost: Decimal | None = Field(default=None, ge=0)
    sale_price: Decimal | None = Field(default=None, ge=0)
    uom: str | None = None
    routes: list[str] = Field(default_factory=list)
    bom_ids: list[str] = Field(default_factory=list)
    capacity_ml: Decimal | None = Field(default=None, ge=0)
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    native_metadata: dict[str, Any] = Field(default_factory=dict)


class SalesOrderLine(CanonicalModel):
    id: str
    native_id: str
    product: Product
    quantity: Decimal = Field(ge=0)
    uom: str | None = None
    unit_price: Decimal = Field(default=Decimal("0"), ge=0)
    subtotal: Decimal = Field(default=Decimal("0"), ge=0)
    tax_ids: list[str] = Field(default_factory=list)
    route_policy: str = "unknown"
    formula_lines: list[FormulaLine] = Field(default_factory=list)
    formula_validation: FormulaValidationSummary | None = None
    custom_attributes: dict[str, Any] = Field(default_factory=dict)
    native_metadata: dict[str, Any] = Field(default_factory=dict)


class SalesOrder(CanonicalModel):
    id: str
    native_id: str
    reference: str
    company: Company | None = None
    customer: Customer | None = None
    state: SalesOrderState = SalesOrderState.UNKNOWN
    order_date: datetime | None = None
    currency: str | None = None
    total_amount: Decimal = Field(default=Decimal("0"), ge=0)
    untaxed_amount: Decimal | None = Field(default=None, ge=0)
    tax_amount: Decimal | None = Field(default=None, ge=0)
    lines: list[SalesOrderLine] = Field(default_factory=list)
    invoice_policy: str = "unknown"
    warehouse: dict[str, Any] | None = None
    native_metadata: dict[str, Any] = Field(default_factory=dict)
