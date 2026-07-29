from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ReplayCreateRequest(BaseModel):
    object_type: str = Field(min_length=1)


class ReplayResponse(BaseModel):
    id: str
    tenant_id: str
    process_key: str
    version: str
    object_type: str
    status: str
    policy_version: str
    connector_simulator_version: str
    case_count: int
    created_at: str
    completed_at: str | None
    frozen_at: str | None


class ReplayCaseResponse(BaseModel):
    case_id: str
    status: str
    decision_trace: list[dict[str, Any]]
    predicted_effects: list[dict[str, Any]]
    safety_violations: list[dict[str, Any]]
    regressions: list[dict[str, Any]]
    metrics: dict[str, Any]
    deterministic_trace_hash: str
    declared_decision_count: int
    evaluated_decision_count: int
    unsupported_decisions: list[str]
    decision_coverage_rate: float


class ReplayCaseComparisonResponse(BaseModel):
    case_id: str
    baseline_status: str
    candidate_status: str
    status_changed: bool
    hash_matches: bool


class ReplayComparisonResponse(BaseModel):
    baseline_replay_id: str
    candidate_replay_id: str
    matched_case_count: int
    compared_case_count: int
    only_in_baseline_case_ids: list[str]
    only_in_candidate_case_ids: list[str]
    cases: list[ReplayCaseComparisonResponse]
