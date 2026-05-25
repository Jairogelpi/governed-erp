from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DiscoverySearchRequest(BaseModel):
    query: str = ""
    status_filter: str | None = None
    runtime_type_filter: str | None = None
    active_only: bool = False
    limit: int = Field(default=20, ge=1, le=100)


class SkillSearchHitSchema(BaseModel):
    version_id: str
    skill_id: str
    name: str
    status: str
    is_active: bool
    runtime_type: str
    relevance_score: float
    match_reason: str
    guard_names: list[str]
    step_count: int


class DiscoverySearchResponse(BaseModel):
    query: str
    results: list[SkillSearchHitSchema]
    total_found: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class SimilarSkillsRequest(BaseModel):
    version_id: str
    limit: int = Field(default=10, ge=1, le=50)


class SimilarSkillHitSchema(BaseModel):
    version_id: str
    skill_id: str
    name: str
    similarity_score: float
    shared_guards: list[str]
    shared_step_types: list[str]
    status: str
    is_active: bool


class SimilarSkillsResponse(BaseModel):
    reference_version_id: str
    reference_name: str
    similar: list[SimilarSkillHitSchema]
    total_found: int
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class LifecycleEventSchema(BaseModel):
    event_type: str
    from_status: str
    to_status: str
    actor: str
    created_at: Any


class LifecycleSummaryResponse(BaseModel):
    version_id: str
    skill_id: str
    name: str
    status: str
    is_active: bool
    runtime_type: str
    governance_status: str
    has_human_decision: bool
    human_decision: str
    has_activation_request: bool
    has_run_preview: bool
    llm_required: bool
    lifecycle_events: list[LifecycleEventSchema]
    preview_event_count: int
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class GovernanceGapSchema(BaseModel):
    gap_type: str
    description: str
    severity: str
    suggested_action: str


class GovernanceGapsResponse(BaseModel):
    version_id: str
    skill_id: str
    gaps: list[GovernanceGapSchema]
    gap_count: int
    is_fully_governed: bool
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class RecommendationSchema(BaseModel):
    priority: int
    action: str
    description: str
    endpoint_hint: str
    category: str


class RecommendationsResponse(BaseModel):
    version_id: str
    skill_id: str
    recommendations: list[RecommendationSchema]
    governance_complete: bool
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class ReuseSuggestionsRequest(BaseModel):
    query: str = ""
    version_id: str | None = None
    limit: int = Field(default=10, ge=1, le=50)


class ReuseSuggestionSchema(BaseModel):
    version_id: str
    skill_id: str
    name: str
    reuse_rationale: str
    similarity_score: float
    is_active: bool
    governance_complete: bool
    next_step: str


class ReuseSuggestionsResponse(BaseModel):
    query: str
    suggestions: list[ReuseSuggestionSchema]
    total_found: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
