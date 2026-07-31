"""Thin orchestration wiring comparison.py + interpretation.py -- no DB."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from erpguard.domain.outcomes.comparison import compare
from erpguard.domain.outcomes.interpretation import classify
from erpguard.domain.outcomes.types import ObservedMetrics


def measure(
    *,
    comparison_method: str,
    baseline_period_metrics: dict,
    baseline_metric_definition_version: str,
    baseline_currency: str | None,
    observed: ObservedMetrics,
    minimum_data_coverage: float,
    estimated_base: Decimal,
) -> dict[str, Any]:
    if comparison_method == "before_after_with_reference_segment":
        return {
            "blocking_issues": ["comparison_method_not_implemented"],
            "observed_revenue_change": None,
            "observed_margin_change": None,
            "observed_margin_percent_change": None,
            "realized_value": None,
            "variance_from_base_estimate": None,
            "result_classification": "blocked",
            "limitations": ["before_after_with_reference_segment_not_implemented"],
        }

    issues, revenue_change, margin_change, margin_percent_change = compare(
        baseline_period_metrics=baseline_period_metrics,
        baseline_metric_definition_version=baseline_metric_definition_version,
        baseline_currency=baseline_currency,
        observed=observed,
        minimum_data_coverage=minimum_data_coverage,
    )
    if issues:
        return {
            "blocking_issues": issues,
            "observed_revenue_change": None,
            "observed_margin_change": None,
            "observed_margin_percent_change": None,
            "realized_value": None,
            "variance_from_base_estimate": None,
            "result_classification": "blocked",
            "limitations": issues,
        }

    realized_value, variance, classification, limitations = classify(
        observed_margin_change=margin_change,
        estimated_base=estimated_base,
        cost_coverage_rate=observed.cost_coverage_rate,
    )
    return {
        "blocking_issues": [],
        "observed_revenue_change": revenue_change,
        "observed_margin_change": margin_change,
        "observed_margin_percent_change": margin_percent_change,
        "realized_value": realized_value,
        "variance_from_base_estimate": variance,
        "result_classification": classification,
        "limitations": limitations,
    }
