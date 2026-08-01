"""Spec 92 Sec 8.3 -- preconditions for `customer_discount_quote_scenario_v1`.

Pure validation: takes already-parsed `PricingScenarioInputs`, returns the
list of violated preconditions (empty = passes). No I/O, no connector call
-- this runs before `GovernedActionDraft` is even built, so a bad
recommendation never reaches the connector layer at all.
"""

from __future__ import annotations

from decimal import Decimal

from erpguard.config import settings
from erpguard.domain.recommendations.types import PricingScenarioInputs


def validate_pricing_scenario(inputs: PricingScenarioInputs) -> list[str]:
    issues: list[str] = []

    if not settings.allow_pricing_scenario_draft:
        issues.append("pricing_scenario_draft_disabled")

    if not inputs.lines:
        issues.append("pricing_scenario_requires_at_least_one_line")
    if len(inputs.lines) > settings.pricing_scenario_max_lines:
        issues.append(f"pricing_scenario_exceeds_max_lines:{settings.pricing_scenario_max_lines}")

    total = Decimal("0")
    for index, line in enumerate(inputs.lines):
        if line.quantity <= 0:
            issues.append(f"line_{index}_quantity_must_be_positive")
        if line.proposed_unit_price <= 0:
            issues.append(f"line_{index}_price_must_be_positive")
        if line.cost_reference < 0:
            issues.append(f"line_{index}_cost_reference_must_be_non_negative")
        total += line.proposed_unit_price * line.quantity

        if line.cost_reference > 0 and line.proposed_unit_price > 0:
            margin_percent = (line.proposed_unit_price - line.cost_reference) / line.proposed_unit_price * Decimal(100)
            if margin_percent < line.minimum_margin_percent:
                issues.append(f"line_{index}_margin_floor_violated:{margin_percent}")

    if total > Decimal(str(settings.pricing_scenario_max_total)):
        issues.append(f"pricing_scenario_exceeds_max_total:{settings.pricing_scenario_max_total}")

    return issues
