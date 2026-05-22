from __future__ import annotations

from pydantic import BaseModel, Field


class ManualRunRequest(BaseModel):
    target_base_url: str
    actor: str = "manual_operator"
    inputs: dict = Field(default_factory=dict)


class ManualRunResponse(BaseModel):
    run_id: str
    version_id: str
    skill_id: str
    status: str
    replay_run_id: str | None
    steps_passed: int
    steps_failed: int
    steps_verification_failed: int
    summary: str
    actor: str
    target_base_url: str
    inputs: dict
    gate_checks: list[dict]
    input_validation_checks: list[dict]
    finished_at: str


class RunSummaryResponse(BaseModel):
    run_id: str
    version_id: str
    skill_id: str
    status: str
    actor: str
    trigger: str
    target_base_url: str
    replay_run_id: str | None
    inputs: dict
    gate_result: dict
    input_validation: dict
    summary: dict
    created_at: str
    finished_at: str


class RunEventEntryResponse(BaseModel):
    event_id: str
    run_id: str
    event_type: str
    status: str
    detail: str
    payload: dict
    created_at: str


class RunEventsResponse(BaseModel):
    run_id: str
    event_count: int
    events: list[RunEventEntryResponse]


class RunReportResponse(BaseModel):
    run_id: str
    version_id: str
    skill_id: str
    run_status: str
    actor: str
    trigger: str
    target_base_url: str
    replay_run_id: str | None
    step_count: int
    steps_passed: int
    steps_failed: int
    steps_verification_failed: int
    success_rate_pct: float
    llm_used_at_replay: bool
    deterministic: bool
    failure_count: int
    failures: list[dict]
    verifications: list[dict]
    event_log: list[dict]
    recovery_actions_required: bool
    summary: str
    created_at: str
    finished_at: str
