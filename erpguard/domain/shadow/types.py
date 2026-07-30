from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


ReviewerLabel = Literal[
    "active_preferred",
    "candidate_preferred",
    "equivalent",
    "unsafe_candidate",
    "needs_investigation",
    "insufficient_evidence",
]


class ShadowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ShadowDecision(ShadowModel):
    status: str
    decision_trace: list[dict[str, Any]]
    predicted_effects: list[dict[str, Any]]
    safety_violations: list[dict[str, Any]]
    unsupported_decisions: list[str]
    decision_coverage_rate: float


class ShadowEvaluationInput(ShadowModel):
    case_id: str = Field(min_length=1, max_length=200)
    idempotency_key: str = Field(min_length=1, max_length=256)
    event_types: list[str] = Field(min_length=1, max_length=50)
    object_attributes: dict[str, Any]
    actual_outcome: dict[str, Any] | None = None
