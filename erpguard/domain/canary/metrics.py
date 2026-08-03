"""Spec 92 Sec 9.8 -- canary dashboard aggregation.

`wilson_interval` is the shared Wilson-score confidence-interval helper --
`ShadowService.dashboard` (`erpguard/domain/shadow/service.py`) imports and
calls this same function rather than keeping its own copy.
"""

from __future__ import annotations

from math import sqrt
from typing import Any

RECOMMENDATIONS = {
    "continue_canary",
    "pause_and_investigate",
    "eligible_for_promotion",
    "not_enough_evidence",
    "abort",
}


def wilson_interval(successes: int, total: int) -> dict[str, float] | None:
    if not total:
        return None
    z = 1.959963984540054
    proportion = successes / total
    denominator = 1 + z * z / total
    centre = (proportion + z * z / (2 * total)) / denominator
    margin = z * sqrt((proportion * (1 - proportion) + z * z / (4 * total)) / total) / denominator
    return {"lower": max(0.0, centre - margin), "upper": min(1.0, centre + margin)}


def recommend(
    *,
    canary_case_count: int,
    minimum_cases: int,
    unresolved_critical_incidents: int,
    postcondition_failure_rate: float,
    blocked_rate: float,
) -> str:
    if unresolved_critical_incidents > 0:
        return "abort"
    if canary_case_count < minimum_cases:
        return "not_enough_evidence"
    if postcondition_failure_rate > 0.1 or blocked_rate > 0.2:
        return "pause_and_investigate"
    return "eligible_for_promotion"


def build_dashboard(
    *,
    stable_count: int,
    canary_count: int,
    succeeded_count: int,
    blocked_count: int,
    failed_count: int,
    postcondition_failure_count: int,
    unexpected_side_effect_count: int,
    cumulative_amount: float,
    estimated_opportunity_value: str | None,
    reviewed_incidents: int,
    unresolved_incidents: int,
    minimum_cases: int,
) -> dict[str, Any]:
    total = succeeded_count + blocked_count + failed_count
    blocked_rate = blocked_count / total if total else 0.0
    postcondition_failure_rate = postcondition_failure_count / total if total else 0.0
    return {
        "assigned_stable_cases": stable_count,
        "assigned_canary_cases": canary_count,
        "successful_runs": succeeded_count,
        "blocked_runs": blocked_count,
        "failed_runs": failed_count,
        "postcondition_failures": postcondition_failure_count,
        "unexpected_side_effects": unexpected_side_effect_count,
        "cumulative_amount": cumulative_amount,
        "estimated_opportunity_value": estimated_opportunity_value,
        "reviewed_incidents": reviewed_incidents,
        "unresolved_incidents": unresolved_incidents,
        "success_confidence_interval_95": wilson_interval(succeeded_count, total),
        "recommendation": recommend(
            canary_case_count=canary_count,
            minimum_cases=minimum_cases,
            unresolved_critical_incidents=unresolved_incidents,
            postcondition_failure_rate=postcondition_failure_rate,
            blocked_rate=blocked_rate,
        ),
    }
