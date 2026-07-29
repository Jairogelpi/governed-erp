from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ProofCreateRequest(BaseModel):
    baseline_replay_id: str = Field(min_length=1)
    benchmark_version: str = Field(min_length=1)


class ProofResponse(BaseModel):
    id: str
    tenant_id: str
    baseline_replay_id: str
    candidate_replay_id: str
    dataset_version: str
    benchmark_version: str
    metric_comparisons: list[dict[str, Any]]
    regressions: list[dict[str, Any]]
    safety_summary: dict[str, Any]
    reproducibility_summary: dict[str, Any]
    evidence_refs: list[str]
    recommendation: str
    recommendation_basis: list[str]
    limitations: list[str]
    content_hash: str
    generated_at: str
