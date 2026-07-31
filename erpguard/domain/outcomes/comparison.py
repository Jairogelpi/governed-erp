"""Spec 92 Sec 10.3 -- comparison gates. Pure function, no DB, no I/O.

Fails closed: any refusal condition short-circuits to a blocking-issues
list instead of computing a comparison that wouldn't mean anything.
"""

from __future__ import annotations

from decimal import Decimal

from erpguard.domain.outcomes.types import ObservedMetrics


def _decimal(values: dict, key: str) -> Decimal | None:
    entry = values.get(key)
    if not isinstance(entry, dict):
        return None
    value = entry.get("value")
    return Decimal(str(value)) if value is not None else None


def compare(
    *,
    baseline_period_metrics: dict,
    baseline_metric_definition_version: str,
    baseline_currency: str | None,
    observed: ObservedMetrics,
    minimum_data_coverage: float,
) -> tuple[list[str], Decimal | None, Decimal | None, Decimal | None]:
    """Returns (blocking_issues, observed_revenue_change, observed_margin_change,
    observed_margin_percent_change). Non-empty blocking_issues means the
    deltas are None and the caller must not report a numeric comparison."""

    issues: list[str] = []

    baseline_values = baseline_period_metrics.get("values", {})
    if baseline_metric_definition_version != observed.metric_definition_version:
        issues.append("metric_definition_version_mismatch")

    if baseline_currency is None or observed.currency is None or baseline_currency != observed.currency:
        issues.append("currency_not_comparable")

    if observed.cost_coverage_rate < minimum_data_coverage:
        issues.append(f"insufficient_data_coverage:{observed.cost_coverage_rate}")

    baseline_net_revenue = _decimal(baseline_values, "net_revenue")
    baseline_gross_margin = _decimal(baseline_values, "gross_margin")
    baseline_gross_margin_percent = _decimal(baseline_values, "gross_margin_percent")

    if baseline_net_revenue is None or observed.net_revenue is None:
        issues.append("net_revenue_not_available")
    if baseline_gross_margin is None or observed.gross_margin is None:
        issues.append("gross_margin_not_available")

    if issues:
        return issues, None, None, None

    revenue_change = observed.net_revenue - baseline_net_revenue
    margin_change = observed.gross_margin - baseline_gross_margin
    margin_percent_change = (
        observed.gross_margin_percent - baseline_gross_margin_percent
        if observed.gross_margin_percent is not None and baseline_gross_margin_percent is not None
        else None
    )
    return [], revenue_change, margin_change, margin_percent_change
