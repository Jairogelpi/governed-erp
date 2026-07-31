from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class OpportunityModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OpportunityEvidence(OpportunityModel):
    segment_id: str
    segment_name: str
    comparison_gross_margin_percent: Decimal | None
    current_gross_margin_percent: Decimal | None
    comparison_cost_ratio: Decimal | None
    current_cost_ratio: Decimal | None
    current_net_revenue: Decimal
    segment_impact: Decimal


class OpportunityResult(OpportunityModel):
    cause: str
    affected_population: list[str]
    evidence: list[OpportunityEvidence]
    impact_base: Decimal
    proposed_action: str
