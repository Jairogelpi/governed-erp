"""Historical replay result shapes (master spec section 15.3/15.5).

`ExpectedEffect` mirrors the spec's `ReplayCase` field of the same name for
structural completeness, but this engine derives cases from already-ingested
canonical events rather than curated fixture files with explicit expected
outcomes, so it is not populated by the current engine -- a future fixture-
file-based replay input could use it.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ReplayModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ExpectedEffect(ReplayModel):
    kind: str
    description: str = ""
    evidence: dict[str, Any] = Field(default_factory=dict)


class DecisionTrace(ReplayModel):
    decision_name: str
    applies_to: str
    outcome: str
    policy_id: str
    policy_version: str
    summary: str
    risk_level: str = ""


class PredictedEffect(ReplayModel):
    kind: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class Violation(ReplayModel):
    code: str
    message: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class Regression(ReplayModel):
    """Populated only by a future comparison/regression pass (Phase 13)."""

    kind: str
    description: str
    evidence: dict[str, Any] = Field(default_factory=dict)


class ReplayCaseResult(ReplayModel):
    case_id: str
    status: str
    decision_trace: list[DecisionTrace] = Field(default_factory=list)
    predicted_effects: list[PredictedEffect] = Field(default_factory=list)
    safety_violations: list[Violation] = Field(default_factory=list)
    regressions: list[Regression] = Field(default_factory=list)
    metrics: dict[str, float | int | None] = Field(default_factory=dict)
    deterministic_trace_hash: str
