"""Spec 92 Sec 7.4 -- code-defined, allowlisted action templates.

`execution_classification` is the single source of truth for whether a
template can ever produce an `ExecutionRun`. Nothing downstream may
silently upgrade a `review_only`/`unsupported` template to executable --
`RecommendationService.create_action_draft` reads this table only.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ActionTemplate:
    name: str
    version: str
    execution_classification: str  # "executable" | "review_only" | "unsupported"
    capability: str | None
    connector_id: str | None
    description: str


ACTION_TEMPLATES: dict[str, ActionTemplate] = {
    "customer_discount_quote_scenario_v1": ActionTemplate(
        name="customer_discount_quote_scenario_v1",
        version="1",
        execution_classification="executable",
        capability="sales.quote.create_pricing_scenario_draft",
        connector_id="odoo",
        description=(
            "Create a controlled Odoo draft quotation scenario using proposed "
            "pricing for a selected customer and bounded product set."
        ),
    ),
    "product_price_review_v1": ActionTemplate(
        name="product_price_review_v1",
        version="1",
        execution_classification="review_only",
        capability=None,
        connector_id=None,
        description="Structured internal pricing proposal for affected products; cannot modify Odoo.",
    ),
    "cost_drift_review_v1": ActionTemplate(
        name="cost_drift_review_v1",
        version="1",
        execution_classification="review_only",
        capability=None,
        connector_id=None,
        description="Structured supplier-cost and pricing review; cannot modify Odoo.",
    ),
}


class UnknownActionTemplate(KeyError):
    pass


def get_template(name: str) -> ActionTemplate:
    template = ACTION_TEMPLATES.get(name)
    if template is None:
        raise UnknownActionTemplate(name)
    return template
