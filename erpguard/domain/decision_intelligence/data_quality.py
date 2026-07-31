from __future__ import annotations

from collections import Counter, defaultdict
from decimal import Decimal
from typing import Literal

from erpguard.domain.decision_intelligence.types import (
    DataQualityResult,
    ExtractionDataset,
    QualityCheck,
)


def _rate(count: int, total: int) -> float:
    return count / total if total else 0.0


def evaluate_data_quality(
    dataset: ExtractionDataset,
    *,
    minimum_cost_coverage: float = 0.8,
) -> DataQualityResult:
    lines = dataset.lines
    total = len(lines)
    checks: list[QualityCheck] = []
    errors: list[str] = []
    warnings: list[str] = []
    blocking: list[str] = []

    duplicate_count = total - len({line.invoice_line_id for line in lines})
    duplicate_rate = _rate(duplicate_count, total)
    checks.append(
        QualityCheck(
            code="duplicate_invoice_lines",
            dimension="uniqueness",
            severity="critical",
            status="failed" if duplicate_count else "passed",
            affected_count=duplicate_count,
            affected_rate=duplicate_rate,
            message="Invoice-line identifiers must be unique at the analytical grain.",
        )
    )
    if duplicate_count:
        blocking.append("duplicate_invoice_line_grain")
        errors.append("Duplicate invoice lines would overstate revenue and margin.")

    non_posted = sum(line.move_state != "posted" for line in lines)
    checks.append(
        QualityCheck(
            code="posted_move_scope",
            dimension="validity",
            severity="critical",
            status="failed" if non_posted else "passed",
            affected_count=non_posted,
            affected_rate=_rate(non_posted, total),
            message="Only posted customer invoices and refunds may enter canonical revenue.",
        )
    )
    if non_posted:
        blocking.append("non_posted_moves_present")

    currencies = sorted({line.currency for line in lines})
    mixed_currency = len(currencies) > 1
    checks.append(
        QualityCheck(
            code="single_currency_scope",
            dimension="consistency",
            severity="critical",
            status="failed" if mixed_currency else "passed",
            affected_count=total if mixed_currency else 0,
            affected_rate=1.0 if mixed_currency else 0.0,
            message="Metrics cannot aggregate currencies without a versioned conversion source.",
        )
    )
    if mixed_currency:
        blocking.append("mixed_currencies_without_conversion")
        errors.append("Multiple currencies require a governed conversion layer.")

    revenue_weight = sum(abs(line.price_subtotal) for line in lines)
    valid_revenue_weight = sum(
        abs(line.price_subtotal)
        for line in lines
        if line.move_state == "posted" and line.currency and line.invoice_date
    )
    revenue_coverage = (
        float(valid_revenue_weight / revenue_weight)
        if revenue_weight
        else (1.0 if not lines else 0.0)
    )
    checks.append(
        QualityCheck(
            code="revenue_field_coverage",
            dimension="completeness",
            severity="high",
            status="passed" if revenue_coverage >= 0.99 else "failed",
            affected_count=sum(
                not (line.currency and line.invoice_date and line.move_state == "posted")
                for line in lines
            ),
            affected_rate=1 - revenue_coverage,
            message="Revenue requires posted state, invoice date and currency.",
        )
    )
    if revenue_coverage < 0.99:
        blocking.append("insufficient_revenue_coverage")

    cost_weight = sum(abs(line.price_subtotal) for line in lines if line.cost.unit_cost is not None)
    cost_coverage = float(cost_weight / revenue_weight) if revenue_weight else 0.0
    missing_cost = sum(line.cost.unit_cost is None for line in lines)
    checks.append(
        QualityCheck(
            code="cost_coverage",
            dimension="completeness",
            severity="critical",
            status=("passed" if cost_coverage >= minimum_cost_coverage else "failed"),
            affected_count=missing_cost,
            affected_rate=1 - cost_coverage,
            message="Gross margin requires explicit cost evidence for material revenue.",
        )
    )
    if cost_coverage < minimum_cost_coverage:
        blocking.append("insufficient_cost_coverage")
        errors.append(
            "Revenue is usable, but gross margin is blocked by insufficient cost coverage."
        )

    current_cost_count = sum(line.cost.source == "current_standard_price" for line in lines)
    checks.append(
        QualityCheck(
            code="historical_cost_reliability",
            dimension="timeliness",
            severity="high",
            status="warning" if current_cost_count else "passed",
            affected_count=current_cost_count,
            affected_rate=_rate(current_cost_count, total),
            message=(
                "Current standard price is not historical cost and is disclosed as a low-reliability fallback."
            ),
        )
    )
    if current_cost_count:
        warnings.append("Some cost uses current standard price rather than historical valuation.")

    refunds = [line for line in lines if line.move_type == "out_refund"]
    reconciled_refunds = sum(line.reversed_entry_id is not None for line in refunds)
    refund_rate = _rate(reconciled_refunds, len(refunds)) if refunds else 1.0
    checks.append(
        QualityCheck(
            code="refund_reconciliation",
            dimension="integrity",
            severity="medium",
            status="passed" if refund_rate >= 0.95 else "warning",
            affected_count=len(refunds) - reconciled_refunds,
            affected_rate=1 - refund_rate,
            message="Refunds should retain a reversal link where Odoo provides one.",
        )
    )
    if refund_rate < 0.95:
        warnings.append("Some refunds cannot be reconciled to an original invoice.")

    lines_without_product = sum(line.product_id is None for line in lines)
    checks.append(
        QualityCheck(
            code="product_link_coverage",
            dimension="integrity",
            severity="medium",
            status="warning" if lines_without_product else "passed",
            affected_count=lines_without_product,
            affected_rate=_rate(lines_without_product, total),
            message="Product segmentation requires a linked product.",
        )
    )
    if lines_without_product:
        warnings.append("Lines without products are excluded from product-driver rankings.")

    anomalous = sum(
        abs(line.quantity) > Decimal("1000000") or abs(line.price_unit) > Decimal("1000000000")
        for line in lines
    )
    checks.append(
        QualityCheck(
            code="numeric_range",
            dimension="validity",
            severity="high",
            status="warning" if anomalous else "passed",
            affected_count=anomalous,
            affected_rate=_rate(anomalous, total),
            message="Extreme quantities or prices require operator review.",
        )
    )
    if anomalous:
        warnings.append("Extreme quantity or price values were detected.")

    partner_names: dict[str, set[int]] = defaultdict(set)
    for line in lines:
        normalized = " ".join(line.partner_name.casefold().split())
        if normalized:
            partner_names[normalized].add(line.partner_id)
    duplicate_customer_ids = sum(len(ids) for ids in partner_names.values() if len(ids) > 1)
    checks.append(
        QualityCheck(
            code="possible_duplicate_customers",
            dimension="uniqueness",
            severity="medium",
            status="warning" if duplicate_customer_ids else "passed",
            affected_count=duplicate_customer_ids,
            affected_rate=_rate(duplicate_customer_ids, len({line.partner_id for line in lines})),
            message="Normalized customer names mapping to several IDs may split customer metrics.",
        )
    )
    if duplicate_customer_ids:
        warnings.append("Possible duplicate customer identities may fragment customer analysis.")

    low_reliability_share = _rate(
        Counter(line.cost.reliability for line in lines)["low"],
        total,
    )
    if blocking:
        grade: Literal["A", "B", "C", "blocked"] = "blocked"
    elif cost_coverage >= 0.95 and low_reliability_share <= 0.1 and not warnings:
        grade = "A"
    elif cost_coverage >= 0.9 and low_reliability_share <= 0.5:
        grade = "B"
    else:
        grade = "C"
    return DataQualityResult(
        checks=checks,
        errors=errors,
        warnings=warnings,
        cost_coverage_rate=cost_coverage,
        revenue_coverage_rate=revenue_coverage,
        duplicate_rate=duplicate_rate,
        refund_reconciliation_rate=refund_rate,
        confidence_grade=grade,
        blocking_issues=sorted(set(blocking)),
    )
