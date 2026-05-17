from decimal import Decimal

from erpguard.canonical.objects import FormulaValidationError, FormulaValidationSummary, SalesOrder, SalesOrderLine


def validate_sales_order_formulas(sales_order: SalesOrder) -> FormulaValidationSummary:
    errors: list[FormulaValidationError] = []
    checked_lines_count = 0
    skipped_lines_count = 0

    if not sales_order.lines:
        errors.append(
            FormulaValidationError(
                code="sales_order_has_no_lines",
                line_id=None,
                product_name=None,
                expected_ml=None,
                actual_ml=None,
                message="Sales order has no lines to validate.",
                evidence={"sales_order_id": sales_order.id, "reference": sales_order.reference},
            )
        )
        return _summary(checked_lines_count, skipped_lines_count, errors)

    for line in sales_order.lines:
        capacity_ml = line.product.capacity_ml
        if capacity_ml is None:
            skipped_lines_count += 1
            continue

        checked_lines_count += 1
        if _has_negative_values(line):
            errors.append(
                _error(
                    code="formula_negative_value",
                    line=line,
                    expected_ml=capacity_ml,
                    actual_ml=None,
                    message="Formula validation found a negative value.",
                )
            )
            continue

        if not line.formula_lines:
            errors.append(
                _error(
                    code="formula_missing",
                    line=line,
                    expected_ml=capacity_ml,
                    actual_ml=Decimal("0"),
                    message="Product has a capacity requirement but the sales order line has no formula.",
                )
            )
            continue

        actual_ml_per_unit = sum((_formula_ml_per_unit(formula) for formula in line.formula_lines), Decimal("0"))
        if actual_ml_per_unit != capacity_ml:
            errors.append(
                _error(
                    code="formula_ml_per_unit_mismatch",
                    line=line,
                    expected_ml=capacity_ml,
                    actual_ml=actual_ml_per_unit,
                    message="Formula ml per unit does not match product capacity.",
                )
            )
            continue

        expected_total_ml = capacity_ml * line.quantity
        actual_total_ml = sum((_formula_ml_total(formula, line.quantity) for formula in line.formula_lines), Decimal("0"))
        if actual_total_ml != expected_total_ml:
            errors.append(
                _error(
                    code="formula_total_ml_mismatch",
                    line=line,
                    expected_ml=expected_total_ml,
                    actual_ml=actual_total_ml,
                    message="Formula total ml does not match capacity times ordered quantity.",
                )
            )

    return _summary(checked_lines_count, skipped_lines_count, errors)


def _formula_ml_per_unit(formula) -> Decimal:
    if formula.ml_per_unit is not None:
        return formula.ml_per_unit
    return formula.ml


def _formula_ml_total(formula, quantity: Decimal) -> Decimal:
    if formula.ml_total is not None:
        return formula.ml_total
    return _formula_ml_per_unit(formula) * quantity


def _has_negative_values(line: SalesOrderLine) -> bool:
    if line.quantity < 0:
        return True
    if line.product.capacity_ml is not None and line.product.capacity_ml < 0:
        return True
    return any(
        value is not None and value < 0
        for formula in line.formula_lines
        for value in (formula.ml, formula.ml_per_unit, formula.ml_total)
    )


def _error(
    code: str,
    line: SalesOrderLine,
    expected_ml: Decimal | None,
    actual_ml: Decimal | None,
    message: str,
) -> FormulaValidationError:
    return FormulaValidationError(
        code=code,
        line_id=line.id,
        product_name=line.product.name,
        expected_ml=expected_ml,
        actual_ml=actual_ml,
        message=message,
        evidence={
            "line_id": line.id,
            "product_id": line.product.id,
            "product_name": line.product.name,
            "quantity": line.quantity,
            "capacity_ml": line.product.capacity_ml,
            "expected_ml": expected_ml,
            "actual_ml": actual_ml,
        },
    )


def _summary(
    checked_lines_count: int,
    skipped_lines_count: int,
    errors: list[FormulaValidationError],
) -> FormulaValidationSummary:
    return FormulaValidationSummary(
        is_valid=len(errors) == 0,
        checked_lines_count=checked_lines_count,
        skipped_lines_count=skipped_lines_count,
        error_count=len(errors),
        errors=errors,
        warnings=[],
    )
