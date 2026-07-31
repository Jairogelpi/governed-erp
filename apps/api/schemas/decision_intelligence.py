from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnalyticalSnapshotCreateRequest(BaseModel):
    connection_id: str = Field(min_length=1, max_length=128)
    company_ids: list[int] = Field(default_factory=list, max_length=20)
    period_start: str = Field(min_length=10, max_length=10)
    period_end: str = Field(min_length=10, max_length=10)
    comparison_period_start: str = Field(min_length=10, max_length=10)
    comparison_period_end: str = Field(min_length=10, max_length=10)
    max_rows_per_model: int = Field(default=5000, ge=1, le=20000)
    minimum_cost_coverage: float = Field(default=0.8, ge=0, le=1)


class DataQualityResponse(BaseModel):
    id: str
    checks: list[dict[str, Any]]
    errors: list[str]
    warnings: list[str]
    cost_coverage_rate: float
    revenue_coverage_rate: float
    duplicate_rate: float
    refund_reconciliation_rate: float
    confidence_grade: str
    blocking_issues: list[str]
    content_hash: str


class AnalyticalSnapshotResponse(BaseModel):
    id: str
    tenant_id: str
    connection_id: str
    company_ids: list[int]
    period_start: str
    period_end: str
    comparison_period_start: str
    comparison_period_end: str
    source_models: list[str]
    extraction_manifest: dict[str, Any]
    row_counts: dict[str, int]
    currency: str | None
    source_hash: str
    metric_definition_version: str
    status: str
    created_by: str
    created_at: str
    data_quality: DataQualityResponse
    read_only: bool = True


class MarginAnalysisCreateRequest(BaseModel):
    tolerance: float = Field(default=0.01, gt=0, le=1)


class MarginAnalysisResponse(BaseModel):
    id: str
    tenant_id: str
    snapshot_id: str
    status: str
    metric_definition_version: str
    current_metrics: dict[str, Any]
    comparison_metrics: dict[str, Any]
    margin_bridge: dict[str, Any]
    product_drivers: dict[str, list[dict[str, Any]]]
    customer_drivers: dict[str, list[dict[str, Any]]]
    warnings: list[str]
    tolerance: float
    content_hash: str
    created_by: str
    created_at: str
    read_only: bool = True
