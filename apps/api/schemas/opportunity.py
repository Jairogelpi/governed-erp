from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class MarginOpportunityGenerateRequest(BaseModel):
    pass


class MarginOpportunityResponse(BaseModel):
    id: str
    tenant_id: str
    margin_analysis_id: str
    snapshot_id: str
    cause: str
    affected_population: list[str]
    evidence: list[dict[str, Any]]
    impact_conservative: str
    impact_base: str
    impact_optimistic: str
    confidence_band: str
    risk_level: str
    implementation_cost: str | None
    payback_period_days: int | None
    proposed_action: str
    status: str
    content_hash: str
    created_by: str
    created_at: str
    read_only: bool = True


class MarginOpportunityListResponse(BaseModel):
    margin_analysis_id: str
    blocked: bool
    opportunities: list[MarginOpportunityResponse]
