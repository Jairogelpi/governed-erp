from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from erpguard.domain.shadow.types import ReviewerLabel


class ShadowDeploymentCreateRequest(BaseModel):
    candidate_id: str = Field(min_length=1)
    proof_id: str = Field(min_length=1)
    object_type: str = Field(default="sales_order", min_length=1)
    agreement_threshold: float = Field(default=0.9, ge=0, le=1)


class ShadowDeploymentResponse(BaseModel):
    id: str
    tenant_id: str
    candidate_id: str
    proof_id: str
    process_key: str
    active_version: str
    candidate_version: str
    object_type: str
    status: str
    agreement_threshold: float
    no_effects: bool
    created_by: str
    created_at: str


class ShadowCaseEvaluateRequest(BaseModel):
    case_id: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=256)
    event_types: list[str] = Field(min_length=1, max_length=50)
    object_attributes: dict[str, Any]
    actual_outcome: dict[str, Any] | None = None


class ShadowReviewRequest(BaseModel):
    label: ReviewerLabel
    notes: str = Field(default="", max_length=2000)


class ShadowReviewResponse(BaseModel):
    id: str
    reviewer_id: str
    label: ReviewerLabel
    notes: str
    created_at: str


class ShadowCaseResponse(BaseModel):
    id: str
    deployment_id: str
    case_id: str
    active_decision: dict[str, Any]
    candidate_decision: dict[str, Any]
    agreement: bool
    difference_categories: list[str]
    actual_outcome: dict[str, Any] | None
    reviewer_label: ReviewerLabel | None
    reviews: list[ShadowReviewResponse]
    deterministic_hash: str
    evaluated_at: str


class ShadowDashboardResponse(BaseModel):
    deployment_id: str
    status: str
    no_effects: bool
    evaluated_case_count: int
    agreement_count: int
    disagreement_count: int
    agreement_rate: float | None
    agreement_threshold: float
    threshold_met: bool
    difference_category_counts: dict[str, int]
    review_label_counts: dict[str, int]
    review_count: int
