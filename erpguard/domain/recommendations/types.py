from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class RecommendationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BusinessRationale(RecommendationModel):
    summary: str
    cause: str
    evidence_segment_ids: list[str]


class PricingLineInput(RecommendationModel):
    product_id: int
    quantity: int
    proposed_unit_price: Decimal
    cost_reference: Decimal
    minimum_margin_percent: Decimal


class PricingScenarioInputs(RecommendationModel):
    partner_id: int
    company_id: int
    currency_id: int
    pricelist_id: int
    lines: list[PricingLineInput]
