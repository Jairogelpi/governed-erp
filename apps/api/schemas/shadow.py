from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from erpguard.domain.shadow.types import (
    ObservedDecisionStatus,
    OutcomeProvenance,
    ReviewerLabel,
)


class ShadowDeploymentCreateRequest(BaseModel):
    candidate_id: str = Field(min_length=1)
    proof_id: str = Field(min_length=1)
    object_type: str = Field(default="sales_order", min_length=1)
    agreement_threshold: float = Field(default=0.9, ge=0, le=1)
    minimum_case_count: int = Field(default=30, ge=1, le=1000000)
    minimum_decision_coverage: float = Field(default=1.0, ge=0, le=1)
    minimum_review_coverage: float = Field(default=0.5, ge=0, le=1)
    minimum_outcome_reconciliation: float = Field(default=0.5, ge=0, le=1)
    observation_window_hours: int = Field(default=168, ge=0, le=8760)


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
    reference_version: str
    minimum_case_count: int
    minimum_decision_coverage: float
    minimum_review_coverage: float
    minimum_outcome_reconciliation: float
    observation_window_hours: int
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


class ShadowOutcomeRequest(BaseModel):
    idempotency_key: str = Field(min_length=1, max_length=256)
    outcome: dict[str, Any]
    observed_decision_status: ObservedDecisionStatus | None = None
    provenance: OutcomeProvenance
    source_event_ids: list[str] = Field(default_factory=list, max_length=100)
    observed_at: str = Field(min_length=1, max_length=100)


class ShadowOutcomeResponse(BaseModel):
    id: str
    recorded_by: str
    outcome: dict[str, Any]
    observed_decision_status: ObservedDecisionStatus | None
    provenance: OutcomeProvenance
    source_event_ids: list[str]
    observed_at: str
    deterministic_hash: str
    created_at: str


class ShadowFeedProcessRequest(BaseModel):
    case_ids: list[str] | None = Field(default=None, max_length=200)


class ShadowFeedProcessResponse(BaseModel):
    feed_run_id: str
    deployment_id: str
    scanned_case_count: int
    evaluated_case_count: int
    deduplicated_case_count: int
    failed_case_count: int
    failure_codes: list[str]
    no_effects: bool


class ShadowCaseResponse(BaseModel):
    id: str
    deployment_id: str
    case_id: str
    active_decision: dict[str, Any]
    candidate_decision: dict[str, Any]
    agreement: bool
    difference_categories: list[str]
    actual_outcome: dict[str, Any] | None
    actual_outcome_provenance: OutcomeProvenance | None
    outcome_observations: list[ShadowOutcomeResponse]
    reviewer_label: ReviewerLabel | None
    reviews: list[ShadowReviewResponse]
    evaluation_mode: str
    canonical_trace_hash: str | None
    trace_provenance: dict[str, Any]
    variant_id: str | None
    event_count: int
    first_event_at: str | None
    last_event_at: str | None
    deterministic_hash: str
    evaluated_at: str


class ShadowDashboardResponse(BaseModel):
    deployment_id: str
    status: str
    no_effects: bool
    evaluated_case_count: int
    operational_case_count: int
    agreement_count: int
    disagreement_count: int
    agreement_rate: float | None
    agreement_threshold: float
    threshold_met: bool
    difference_category_counts: dict[str, int]
    review_label_counts: dict[str, int]
    review_count: int
    canonical_case_count: int | None
    case_coverage_rate: float | None
    decision_coverage_rate: float
    review_coverage_rate: float
    outcome_reconciliation_rate: float
    candidate_preferred_rate: float
    unsafe_candidate_rate: float
    insufficient_evidence_rate: float
    outcome_accuracy: float | None
    variant_distribution: dict[str, int]
    agreement_confidence_interval_95: dict[str, float] | None
    outcome_accuracy_confidence_interval_95: dict[str, float] | None
    observation_window_completed: bool
    canary_eligibility_checks: dict[str, bool]
    recommendation: str
    recommendation_is_advisory: bool
