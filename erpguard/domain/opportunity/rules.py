"""Phase 16.6 deterministic opportunity detection rules.

Every rule reads only fields `SegmentMetric`
(`erpguard/domain/decision_intelligence/types.py`) actually carries --
`net_revenue`, `cost_of_sales`, `gross_margin`, `gross_margin_percent` --
paired current vs. comparison per segment. `gross_margin_percent` is in
percent units (35 means 35%, see `metrics.py`'s `* HUNDRED`), so a delta in
percent points is converted to currency by dividing by 100 before applying
it to `current_net_revenue`. Nothing here estimates price, quantity, or
discount depth per segment -- that data doesn't exist at this grain.
"""

from __future__ import annotations

from decimal import Decimal

from erpguard.domain.opportunity.types import OpportunityEvidence, OpportunityResult

HUNDRED = Decimal("100")
MIN_EROSION_PERCENT_POINTS = Decimal("0.01")


def _index_by_segment(rows: list[dict]) -> dict[str, dict]:
    return {row["segment_id"]: row for row in rows}


def _decimal(row: dict, key: str) -> Decimal | None:
    value = row.get(key)
    return Decimal(str(value)) if value is not None else None


def _cost_ratio(row: dict) -> Decimal | None:
    net_revenue = _decimal(row, "net_revenue")
    cost_of_sales = _decimal(row, "cost_of_sales")
    if not net_revenue or cost_of_sales is None:
        return None
    return cost_of_sales / net_revenue * HUNDRED


def margin_percent_erosion(
    driver_pair: dict, *, cause: str, proposed_action: str
) -> OpportunityResult | None:
    current_by_id = _index_by_segment(driver_pair.get("current", []))
    comparison_by_id = _index_by_segment(driver_pair.get("comparison", []))

    evidence: list[OpportunityEvidence] = []
    total_impact = Decimal("0")
    for segment_id, current_row in current_by_id.items():
        comparison_row = comparison_by_id.get(segment_id)
        if comparison_row is None:
            continue
        current_gmp = _decimal(current_row, "gross_margin_percent")
        comparison_gmp = _decimal(comparison_row, "gross_margin_percent")
        current_net_revenue = _decimal(current_row, "net_revenue")
        if current_gmp is None or comparison_gmp is None or current_net_revenue is None:
            continue
        delta = comparison_gmp - current_gmp
        if delta <= MIN_EROSION_PERCENT_POINTS:
            continue
        segment_impact = delta / HUNDRED * current_net_revenue
        total_impact += segment_impact
        evidence.append(
            OpportunityEvidence(
                segment_id=segment_id,
                segment_name=current_row.get("segment_name", segment_id),
                comparison_gross_margin_percent=comparison_gmp,
                current_gross_margin_percent=current_gmp,
                comparison_cost_ratio=_cost_ratio(comparison_row),
                current_cost_ratio=_cost_ratio(current_row),
                current_net_revenue=current_net_revenue,
                segment_impact=segment_impact,
            )
        )

    if not evidence:
        return None
    return OpportunityResult(
        cause=cause,
        affected_population=[item.segment_id for item in evidence],
        evidence=evidence,
        impact_base=total_impact,
        proposed_action=proposed_action,
    )


def cost_drift(driver_pair: dict) -> OpportunityResult | None:
    current_by_id = _index_by_segment(driver_pair.get("current", []))
    comparison_by_id = _index_by_segment(driver_pair.get("comparison", []))

    evidence: list[OpportunityEvidence] = []
    total_impact = Decimal("0")
    for segment_id, current_row in current_by_id.items():
        comparison_row = comparison_by_id.get(segment_id)
        if comparison_row is None:
            continue
        current_ratio = _cost_ratio(current_row)
        comparison_ratio = _cost_ratio(comparison_row)
        current_net_revenue = _decimal(current_row, "net_revenue")
        if current_ratio is None or comparison_ratio is None or current_net_revenue is None:
            continue
        delta = current_ratio - comparison_ratio
        if delta <= MIN_EROSION_PERCENT_POINTS:
            continue
        segment_impact = delta / HUNDRED * current_net_revenue
        total_impact += segment_impact
        evidence.append(
            OpportunityEvidence(
                segment_id=segment_id,
                segment_name=current_row.get("segment_name", segment_id),
                comparison_gross_margin_percent=_decimal(comparison_row, "gross_margin_percent"),
                current_gross_margin_percent=_decimal(current_row, "gross_margin_percent"),
                comparison_cost_ratio=comparison_ratio,
                current_cost_ratio=current_ratio,
                current_net_revenue=current_net_revenue,
                segment_impact=segment_impact,
            )
        )

    if not evidence:
        return None
    return OpportunityResult(
        cause="cost_drift",
        affected_population=[item.segment_id for item in evidence],
        evidence=evidence,
        impact_base=total_impact,
        proposed_action="Renegotiate supplier cost or reprice affected products to absorb cost drift.",
    )


def detect_opportunities(
    *, product_drivers: dict, customer_drivers: dict
) -> list[OpportunityResult]:
    results: list[OpportunityResult] = []

    product_erosion = margin_percent_erosion(
        product_drivers,
        cause="product_margin_percent_erosion",
        proposed_action="Review pricing or discount depth for these products.",
    )
    if product_erosion is not None:
        results.append(product_erosion)

    product_cost_drift = cost_drift(product_drivers)
    if product_cost_drift is not None:
        results.append(product_cost_drift)

    customer_erosion = margin_percent_erosion(
        customer_drivers,
        cause="customer_margin_percent_erosion",
        proposed_action="Review account-specific terms for these customers.",
    )
    if customer_erosion is not None:
        results.append(customer_erosion)

    return results
