from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class MeasurementPlanCreateRequest(BaseModel):
    execution_run_ids: list[str] = Field(default_factory=list)
    comparison_method: str = Field(pattern="^(before_after_same_scope|before_after_with_reference_segment|fixture_replay)$")
    observation_start: str = Field(min_length=10, max_length=10)
    observation_end: str = Field(min_length=10, max_length=10)
    minimum_data_coverage: float = Field(default=0.8, ge=0, le=1)
    target_metrics: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    implementation_cost: Decimal | None = Field(default=None, ge=0)


class MeasurementPlanApproveRequest(BaseModel):
    approval_id: str = Field(min_length=1)


class ObservedMetricsRequest(BaseModel):
    net_revenue: Decimal | None = None
    gross_margin: Decimal | None = None
    gross_margin_percent: Decimal | None = None
    currency: str | None = None
    metric_definition_version: str = Field(min_length=1)
    cost_coverage_rate: float = Field(default=1.0, ge=0, le=1)


class CaptureFollowupRequest(BaseModel):
    """Exactly one of `observed` (fixture/manual_import path) or the two
    `followup_*` ids (live_odoo_read path) must be supplied."""

    observed: ObservedMetricsRequest | None = None
    source: str = Field(default="fixture", pattern="^(fixture|manual_import)$")
    followup_snapshot_id: str | None = None
    followup_analysis_id: str | None = None


class MeasurementPlanResponse(BaseModel):
    id: str
    tenant_id: str
    recommendation_id: str
    margin_opportunity_id: str
    baseline_snapshot_id: str
    baseline_analysis_id: str
    action_draft_id: str
    execution_run_ids: list[str]
    metric_definition_version: str
    target_metrics: list[str]
    comparison_method: str
    observation_start: str
    observation_end: str
    minimum_data_coverage: float
    implementation_cost: str | None
    status: str
    content_hash: str
    approval_scope: str
    created_by: str
    created_at: str
    started_at: str | None
    ready_at: str | None
    evaluated_at: str | None


class OutcomeObservationResponse(BaseModel):
    id: str
    measurement_plan_id: str
    followup_snapshot_id: str | None
    followup_analysis_id: str | None
    source: str
    observed_at: str
    metrics: dict[str, Any]
    created_at: str


class RealizedOutcomeReportResponse(BaseModel):
    id: str
    measurement_plan_id: str
    recommendation_id: str
    opportunity_id: str
    estimated_conservative: str
    estimated_base: str
    estimated_optimistic: str
    observed_revenue_change: str | None
    observed_margin_change: str | None
    observed_margin_percent_change: str | None
    observed_refund_change: str | None
    realized_value: str | None
    implementation_cost: str | None
    net_realized_value: str | None
    variance_from_base_estimate: str | None
    result_classification: str
    confidence_band: str
    limitations: list[str]
    assumptions: list[str]
    metric_definition_version: str
    content_hash: str
    created_by: str
    created_at: str
