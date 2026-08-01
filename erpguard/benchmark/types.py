"""Shared types between configurations, runner, metrics and report -- kept
separate from dataset.py (case definitions) since this module describes
what happened, not what was asked for."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CaseOutcome(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: str
    configuration: str
    final_state: str
    task_success: bool
    unsafe_side_effect: bool
    correctly_blocked: bool
    incorrectly_blocked: bool
    duplicate_created: bool | None = None
    postcondition_checked: bool
    evidence_complete: bool
    approval_required_detected: bool
    latency_ms: float | None = None
    token_cost: float | None = None
    error: str | None = None
    trace_hash: str | None = None
