"""Metric comparisons genuinely derivable from replay case data (spec 17.2).

Only two metrics are computed: `unsafe_case_rate` (directly readable off
each replay's own case statuses) and `false_block_rate` (a byproduct of the
regression classifier's own transition detection). No other metric from the
master spec's example appendix (e.g. `token_increase`) is computed -- there
is nothing in this codebase that measures it.
"""

from __future__ import annotations

from erpguard.domain.proofs.regression_classifier import CaseDetail
from erpguard.domain.proofs.types import Direction, MetricComparison


def _direction(baseline: float, candidate: float) -> Direction:
    if candidate < baseline:
        return "improved"
    if candidate > baseline:
        return "regressed"
    return "unchanged"


def _rate(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 4) if denominator else 0.0


def compute_metric_comparisons(
    *,
    baseline_statuses: list[str],
    candidate_statuses: list[str],
    case_details: list[CaseDetail],
) -> list[MetricComparison]:
    baseline_unsafe = sum(1 for status in baseline_statuses if status == "failed")
    candidate_unsafe = sum(1 for status in candidate_statuses if status == "failed")
    unsafe_case_rate = MetricComparison(
        metric="unsafe_case_rate",
        baseline=_rate(baseline_unsafe, len(baseline_statuses)),
        candidate=_rate(candidate_unsafe, len(candidate_statuses)),
        direction=_direction(_rate(baseline_unsafe, len(baseline_statuses)), _rate(candidate_unsafe, len(candidate_statuses))),
    )

    false_block_count = sum(1 for detail in case_details if detail["category"] == "false_block")
    denominator = len(candidate_statuses) or 1
    false_block_rate = MetricComparison(
        metric="false_block_rate",
        baseline=0.0,
        candidate=_rate(false_block_count, denominator),
        direction=_direction(0.0, _rate(false_block_count, denominator)),
    )

    return [unsafe_case_rate, false_block_rate]
