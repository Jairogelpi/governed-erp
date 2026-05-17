from copy import deepcopy
from decimal import Decimal

from erpguard.adapters.base import ERPAdapter
from erpguard.canonical.enums import CanonicalAction, ERPType, ProductTracking, ProductType, SalesOrderState
from erpguard.canonical.objects import (
    Company,
    Customer,
    FormulaLine,
    FormulaValidationSummary,
    Product,
    SalesOrder,
    SalesOrderLine,
)
from erpguard.core.errors import ObjectNotFoundError


class FakeERPAdapter(ERPAdapter):
    def __init__(self) -> None:
        self._orders = _build_fake_orders()

    def get_erp_type(self) -> ERPType:
        return ERPType.FAKE

    def health_check(self) -> dict:
        return {
            "status": "ok",
            "erp_type": ERPType.FAKE.value,
            "adapter": self.__class__.__name__,
        }

    def get_sales_order(self, order_id: str) -> SalesOrder:
        try:
            return deepcopy(self._orders[order_id])
        except KeyError as exc:
            raise ObjectNotFoundError(f"SalesOrder '{order_id}' was not found in fake ERP adapter.") from exc

    def get_sales_order_by_reference(self, reference: str) -> SalesOrder:
        for order in self._orders.values():
            if order.reference == reference:
                return deepcopy(order)
        raise ObjectNotFoundError(f"SalesOrder reference '{reference}' was not found in fake ERP adapter.")

    def inspect_permissions(
        self,
        actor_id: str,
        canonical_action: CanonicalAction,
        target_object: str,
        target_id: str,
    ) -> dict:
        return {
            "actor_id": actor_id,
            "canonical_action": canonical_action.value,
            "target_object": target_object,
            "target_id": target_id,
            "allowed": True,
            "source": ERPType.FAKE.value,
        }

    def list_supported_actions(self) -> list[CanonicalAction]:
        return [
            CanonicalAction.INSPECT_SALES_ORDER,
            CanonicalAction.CONFIRM_SALES_ORDER,
            CanonicalAction.VALIDATE_FORMULA,
            CanonicalAction.INSPECT_ACCESS_RULES,
        ]


def _build_fake_orders() -> dict[str, SalesOrder]:
    company = Company(id="company_fake", native_id="fake_company_1", name="Fake ERP Company", currency="EUR")
    customer = Customer(id="customer_fake", native_id="fake_customer_1", name="Fake Customer", active=True)
    product = Product(
        id="product_mikado_100",
        native_id="fake_product_100",
        sku="MIKADO-100",
        name="Mikado 100 ML",
        active=True,
        type=ProductType.STOCKABLE,
        tracking=ProductTracking.LOT,
        capacity_ml=Decimal("100"),
    )

    return {
        "so_valid": SalesOrder(
            id="so_valid",
            native_id="fake_so_1",
            reference="SO-VALID",
            company=company,
            customer=customer,
            state=SalesOrderState.DRAFT,
            currency="EUR",
            total_amount=Decimal("25.00"),
            lines=[
                SalesOrderLine(
                    id="line_valid",
                    native_id="fake_line_1",
                    product=product,
                    quantity=Decimal("2"),
                    unit_price=Decimal("12.50"),
                    subtotal=Decimal("25.00"),
                    formula_lines=[
                        FormulaLine(component_name="Alcohol", ml=Decimal("80")),
                        FormulaLine(component_name="Fragrance", ml=Decimal("20")),
                    ],
                    formula_validation=FormulaValidationSummary(
                        required_ml_per_unit=Decimal("100"),
                        actual_ml_per_unit=Decimal("100"),
                        expected_total_ml=Decimal("200"),
                        actual_total_ml=Decimal("200"),
                        is_valid=True,
                    ),
                )
            ],
        ),
        "so_empty_lines": SalesOrder(
            id="so_empty_lines",
            native_id="fake_so_2",
            reference="SO-EMPTY-LINES",
            company=company,
            customer=customer,
            state=SalesOrderState.DRAFT,
            currency="EUR",
            total_amount=Decimal("0"),
            lines=[],
        ),
        "so_formula_mismatch": SalesOrder(
            id="so_formula_mismatch",
            native_id="fake_so_3",
            reference="SO-FORMULA-MISMATCH",
            company=company,
            customer=customer,
            state=SalesOrderState.DRAFT,
            currency="EUR",
            total_amount=Decimal("25.00"),
            lines=[
                SalesOrderLine(
                    id="line_formula_mismatch",
                    native_id="fake_line_3",
                    product=product,
                    quantity=Decimal("1"),
                    unit_price=Decimal("25.00"),
                    subtotal=Decimal("25.00"),
                    formula_lines=[
                        FormulaLine(component_name="Alcohol", ml=Decimal("60")),
                        FormulaLine(component_name="Fragrance", ml=Decimal("20")),
                    ],
                    formula_validation=FormulaValidationSummary(
                        required_ml_per_unit=Decimal("100"),
                        actual_ml_per_unit=Decimal("80"),
                        expected_total_ml=Decimal("100"),
                        actual_total_ml=Decimal("80"),
                        is_valid=False,
                        message="Formula ml per unit does not match product capacity.",
                    ),
                )
            ],
        ),
        "so_capacity_no_formula": SalesOrder(
            id="so_capacity_no_formula",
            native_id="fake_so_4",
            reference="SO-CAPACITY-NO-FORMULA",
            company=company,
            customer=customer,
            state=SalesOrderState.DRAFT,
            currency="EUR",
            total_amount=Decimal("25.00"),
            lines=[
                SalesOrderLine(
                    id="line_capacity_no_formula",
                    native_id="fake_line_4",
                    product=product,
                    quantity=Decimal("1"),
                    unit_price=Decimal("25.00"),
                    subtotal=Decimal("25.00"),
                    formula_lines=[],
                    formula_validation=None,
                )
            ],
        ),
    }
