"""Proof of Improvement result shapes (master spec section 17.2)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Direction = Literal["improved", "regressed", "unchanged"]
Severity = Literal["critical", "high", "medium", "low", "informational"]
Recommendation = Literal[
    "reject",
    "needs_changes",
    "eligible_for_shadow",
    "eligible_for_canary",
    "eligible_for_promotion",
]


class ProofModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class MetricComparison(ProofModel):
    metric: str
    baseline: float
    candidate: float
    direction: Direction


class RegressionSummary(ProofModel):
    severity: Severity
    category: str
    count: int


class SafetySummary(ProofModel):
    critical_regressions: int
    forbidden_effects: int


class ReproducibilitySummary(ProofModel):
    """What "deterministic" means here: both replays are `completed`/`frozen`
    (never `running`) and every matched case in both replays carries a real,
    persisted `deterministic_trace_hash` -- i.e. the replay engine actually
    ran to completion for it rather than leaving a gap. This does not
    re-execute the policy engine to confirm hash stability; Phase 12's own
    repeatability test (`tests/test_phase12_historical_replay.py`) already
    covers that the engine itself is deterministic. This flag only confirms
    the evidence being cited by the proof is complete and frozen/final.
    """

    baseline_frozen: bool
    candidate_frozen: bool
    deterministic: bool


class ProofOfImprovement(ProofModel):
    proof_id: str
    baseline_process_version_id: str
    candidate_process_version_id: str
    replay_run_id: str
    dataset_version: str
    benchmark_version: str
    metric_comparisons: list[MetricComparison] = Field(default_factory=list)
    regressions: list[RegressionSummary] = Field(default_factory=list)
    safety_summary: SafetySummary
    reproducibility_summary: ReproducibilitySummary
    evidence_refs: list[str] = Field(default_factory=list)
    recommendation: Recommendation
    recommendation_basis: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    generated_at: datetime
    content_hash: str
