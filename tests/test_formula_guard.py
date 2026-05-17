from decimal import Decimal

from erpguard.adapters.fake import FakeERPAdapter
from erpguard.canonical.enums import ProductType
from erpguard.canonical.objects import FormulaLine, Product, SalesOrder, SalesOrderLine
from erpguard.invariants.formula import validate_sales_order_formulas


def make_product(capacity_ml: Decimal | None, name: str = "Mikado 100 ML") -> Product:
    return Product(
        id=f"product_{name.lower().replace(' ', '_')}",
        native_id=f"native_{name.lower().replace(' ', '_')}",
        name=name,
        active=True,
        type=ProductType.STOCKABLE,
        capacity_ml=capacity_ml,
    )


def make_line(
    line_id: str,
    product: Product,
    quantity: Decimal = Decimal("2"),
    formula_lines: list[FormulaLine] | None = None,
) -> SalesOrderLine:
    return SalesOrderLine(
        id=line_id,
        native_id=f"native_{line_id}",
        product=product,
        quantity=quantity,
        formula_lines=formula_lines or [],
    )


def make_formula(line_id: str, ml_per_unit: Decimal, ml_total: Decimal, formula_id: str = "formula_1") -> FormulaLine:
    return FormulaLine(
        id=formula_id,
        sales_order_line_id=line_id,
        fragrance_id="frag_1",
        component_name="Fragrance",
        ml_per_unit=ml_per_unit,
        ml_total=ml_total,
    )


def make_order(lines: list[SalesOrderLine]) -> SalesOrder:
    return SalesOrder(
        id="so_test",
        native_id="native_so_test",
        reference="SO-TEST",
        total_amount=Decimal("0"),
        lines=lines,
    )


def test_product_without_capacity_is_skipped():
    line = make_line("line_skip", make_product(capacity_ml=None))

    summary = validate_sales_order_formulas(make_order([line]))

    assert summary.is_valid is True
    assert summary.checked_lines_count == 0
    assert summary.skipped_lines_count == 1
    assert summary.error_count == 0


def test_valid_formula_passes():
    product = make_product(capacity_ml=Decimal("100"))
    line = make_line("line_valid", product, formula_lines=[make_formula("line_valid", Decimal("100"), Decimal("200"))])

    summary = validate_sales_order_formulas(make_order([line]))

    assert summary.is_valid is True
    assert summary.checked_lines_count == 1
    assert summary.error_count == 0


def test_empty_order_is_invalid():
    summary = validate_sales_order_formulas(make_order([]))

    assert summary.is_valid is False
    assert summary.error_count == 1
    assert summary.errors[0].code == "sales_order_has_no_lines"


def test_capacity_product_with_no_formula_is_invalid():
    product = make_product(capacity_ml=Decimal("100"))
    line = make_line("line_no_formula", product)

    summary = validate_sales_order_formulas(make_order([line]))

    assert summary.is_valid is False
    assert summary.checked_lines_count == 1
    assert summary.error_count == 1
    assert summary.errors[0].code == "formula_missing"
    assert summary.errors[0].line_id == "line_no_formula"
    assert summary.errors[0].product_name == "Mikado 100 ML"
    assert summary.errors[0].expected_ml == Decimal("100")
    assert summary.errors[0].actual_ml == Decimal("0")


def test_formula_ml_per_unit_mismatch_is_invalid():
    product = make_product(capacity_ml=Decimal("100"))
    line = make_line(
        "line_mismatch",
        product,
        formula_lines=[make_formula("line_mismatch", Decimal("80"), Decimal("160"))],
    )

    summary = validate_sales_order_formulas(make_order([line]))

    assert summary.is_valid is False
    assert summary.errors[0].code == "formula_ml_per_unit_mismatch"
    assert summary.errors[0].expected_ml == Decimal("100")
    assert summary.errors[0].actual_ml == Decimal("80")


def test_formula_total_ml_mismatch_is_invalid():
    product = make_product(capacity_ml=Decimal("100"))
    line = make_line(
        "line_total_mismatch",
        product,
        formula_lines=[make_formula("line_total_mismatch", Decimal("100"), Decimal("150"))],
    )

    summary = validate_sales_order_formulas(make_order([line]))

    assert summary.is_valid is False
    assert summary.errors[0].code == "formula_total_ml_mismatch"
    assert summary.errors[0].expected_ml == Decimal("200")
    assert summary.errors[0].actual_ml == Decimal("150")


def test_multiple_formula_lines_sum_correctly():
    product = make_product(capacity_ml=Decimal("100"))
    line = make_line(
        "line_multi",
        product,
        formula_lines=[
            make_formula("line_multi", Decimal("60"), Decimal("120"), formula_id="formula_1"),
            make_formula("line_multi", Decimal("40"), Decimal("80"), formula_id="formula_2"),
        ],
    )

    summary = validate_sales_order_formulas(make_order([line]))

    assert summary.is_valid is True
    assert summary.checked_lines_count == 1
    assert summary.error_count == 0


def test_mixed_order_tracks_skipped_valid_and_invalid_lines():
    skipped = make_line("line_skip", make_product(capacity_ml=None, name="Service"))
    valid_product = make_product(capacity_ml=Decimal("100"), name="Valid Product")
    invalid_product = make_product(capacity_ml=Decimal("50"), name="Invalid Product")
    valid = make_line("line_valid", valid_product, formula_lines=[make_formula("line_valid", Decimal("100"), Decimal("200"))])
    invalid = make_line(
        "line_invalid",
        invalid_product,
        formula_lines=[make_formula("line_invalid", Decimal("40"), Decimal("80"))],
    )

    summary = validate_sales_order_formulas(make_order([skipped, valid, invalid]))

    assert summary.is_valid is False
    assert summary.checked_lines_count == 2
    assert summary.skipped_lines_count == 1
    assert summary.error_count == 1
    assert summary.errors[0].line_id == "line_invalid"
    assert summary.errors[0].product_name == "Invalid Product"


def test_output_includes_line_level_evidence():
    product = make_product(capacity_ml=Decimal("100"), name="Evidence Product")
    line = make_line(
        "line_evidence",
        product,
        formula_lines=[make_formula("line_evidence", Decimal("75"), Decimal("150"))],
    )

    summary = validate_sales_order_formulas(make_order([line]))
    error = summary.errors[0]

    assert error.code == "formula_ml_per_unit_mismatch"
    assert error.line_id == "line_evidence"
    assert error.product_name == "Evidence Product"
    assert error.expected_ml == Decimal("100")
    assert error.actual_ml == Decimal("75")


def test_fake_adapter_fixtures_can_be_validated():
    adapter = FakeERPAdapter()

    valid = validate_sales_order_formulas(adapter.get_sales_order("so_valid"))
    mismatch = validate_sales_order_formulas(adapter.get_sales_order("so_formula_mismatch"))
    missing = validate_sales_order_formulas(adapter.get_sales_order("so_capacity_no_formula"))

    assert valid.is_valid is True
    assert mismatch.is_valid is False
    assert mismatch.errors[0].code == "formula_ml_per_unit_mismatch"
    assert missing.is_valid is False
    assert missing.errors[0].code == "formula_missing"
