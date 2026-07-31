"""Spec 92 Sec 10.5/10.6 -- realized value and classification. Pure function.

`realized_value` = observed gross-margin change within the scoped
population/period (Sec 10.6 v1 definition). Net ROI/payback are never
computed here -- `GovernedRecommendation` carries no implementation-cost
field, so there is nothing evidenced to subtract; this is a documented
limitation, not a nullable field nobody populates.
"""

from __future__ import annotations

from decimal import Decimal

NEUTRAL_TOLERANCE = Decimal("0")
LOW_COVERAGE_INCONCLUSIVE_THRESHOLD = 0.85


def classify(
    *,
    observed_margin_change: Decimal | None,
    estimated_base: Decimal,
    cost_coverage_rate: float,
) -> tuple[Decimal | None, Decimal | None, str, list[str]]:
    """Returns (realized_value, variance_from_base_estimate, classification, limitations)."""

    if observed_margin_change is None:
        return None, None, "blocked", ["comparison_could_not_be_computed"]

    realized_value = observed_margin_change
    variance = realized_value - estimated_base
    limitations: list[str] = []

    if cost_coverage_rate < LOW_COVERAGE_INCONCLUSIVE_THRESHOLD:
        limitations.append(f"borderline_data_coverage:{cost_coverage_rate}")
        return realized_value, variance, "inconclusive", limitations

    if realized_value > NEUTRAL_TOLERANCE:
        classification = "positive_observed_result"
    elif realized_value < NEUTRAL_TOLERANCE:
        classification = "negative_observed_result"
    else:
        classification = "neutral_observed_result"

    limitations.append("no_implementation_cost_evidenced_net_roi_not_computed")
    limitations.append("observed_change_is_not_a_causal_claim")
    return realized_value, variance, classification, limitations
