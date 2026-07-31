from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class RecommendationCreateRequest(BaseModel):
    recommendation_type: str = Field(min_length=1)
    title: str = Field(min_length=1, max_length=256)
    selected_action_template: str = Field(min_length=1)


class RecommendationApproveRequest(BaseModel):
    approval_id: str = Field(min_length=1)


class RecommendationResponse(BaseModel):
    id: str
    tenant_id: str
    margin_opportunity_id: str
    margin_analysis_id: str
    snapshot_id: str
    recommendation_type: str
    title: str
    business_rationale: dict[str, Any]
    affected_population: list[str]
    estimated_impact_conservative: str
    estimated_impact_base: str
    estimated_impact_optimistic: str
    confidence_band: str
    risk_level: str
    selected_action_template: str
    status: str
    source_content_hash: str
    content_hash: str
    approval_scope: str
    created_by: str
    created_at: str
    submitted_at: str | None
    approved_at: str | None
    converted_at: str | None


class PricingLineRequest(BaseModel):
    product_id: int
    quantity: int
    proposed_unit_price: Decimal
    cost_reference: Decimal
    minimum_margin_percent: Decimal


class PricingScenarioInputsRequest(BaseModel):
    partner_id: int
    company_id: int
    currency_id: int
    pricelist_id: int
    lines: list[PricingLineRequest] = Field(default_factory=list)


class ActionDraftCreateRequest(BaseModel):
    process_key: str = Field(min_length=1)
    connection_id: str | None = None
    pricing_inputs: PricingScenarioInputsRequest | None = None


class ActionDraftPlanRunRequest(BaseModel):
    idempotency_key: str = Field(min_length=1)


class ActionDraftResponse(BaseModel):
    id: str
    tenant_id: str
    recommendation_id: str
    action_template: str
    action_template_version: str
    connector_id: str
    process_key: str
    capability: str
    connection_id: str | None
    arguments: dict[str, Any]
    constraints: dict[str, Any]
    execution_classification: str
    status: str
    content_hash: str
    created_by: str
    created_at: str
    validated_at: str | None
    converted_run_id: str | None
    invalidated_at: str | None
