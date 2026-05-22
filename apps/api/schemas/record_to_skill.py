from __future__ import annotations

from pydantic import BaseModel, Field


class CreateSessionRequest(BaseModel):
    name: str
    description: str | None = None
    target_base_url: str


class CreateSessionResponse(BaseModel):
    session_id: str
    name: str
    description: str | None
    target_base_url: str
    status: str
    created_at: str
    updated_at: str


class CaptureEventRequest(BaseModel):
    event_type: str
    url: str | None = None
    selector: str | None = None
    element_text: str | None = None
    element_label: str | None = None
    input_value: str | None = None
    metadata: dict = Field(default_factory=dict)


class CaptureEventResponse(BaseModel):
    event_id: str
    session_id: str
    event_index: int
    event_type: str
    url: str | None
    selector: str | None
    element_text: str | None
    element_label: str | None
    input_value: str | None
    metadata: dict
    created_at: str


class FinishSessionResponse(BaseModel):
    session_id: str
    status: str


class GenerateDraftRequest(BaseModel):
    name: str
    description: str | None = None


class GenerateDraftResponse(BaseModel):
    draft_id: str
    session_id: str
    name: str
    description: str | None
    steps: list[dict]
    selector_map: dict
    guard_names: list[str]
    status: str
    event_count: int
    normalized_event_count: int


class CompileUISkillResponse(BaseModel):
    compiled_skill_id: str
    draft_id: str
    session_id: str
    name: str
    runtime_type: str
    steps: list[dict]
    guard_names: list[str]
    llm_required: bool
    status: str


class ReplayRequest(BaseModel):
    target_base_url: str


class ReplayStepResponse(BaseModel):
    step_index: int
    step_id: str
    step_type: str
    status: str
    before_state: dict
    after_state: dict
    evidence: dict
    error: str | None


class ReplayResponse(BaseModel):
    replay_id: str
    compiled_skill_id: str
    status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    step_results: list[ReplayStepResponse]
    finished_at: str


class AuditStepEntry(BaseModel):
    audit_id: str
    replay_run_id: str
    step_index: int
    step_id: str
    step_type: str
    status: str
    before_state: dict
    after_state: dict
    evidence: dict
    error_text: str | None
    created_at: str


class AuditResponse(BaseModel):
    replay_id: str
    compiled_skill_id: str
    target_base_url: str
    replay_status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    entries: list[AuditStepEntry]


class ReportResponse(BaseModel):
    replay_id: str
    compiled_skill_id: str
    target_base_url: str
    replay_status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    success_rate_pct: float
    llm_used_at_replay: bool
    deterministic: bool
    audit_evidence_count: int
    findings: list[str]
    summary: str


# Sprint 22 — Verification, Failures, Robust Report, Verified Replay

class VerifiedStepResponse(BaseModel):
    step_index: int
    step_id: str
    step_type: str
    status: str
    verification_status: str
    before_state: dict
    after_state: dict
    evidence: dict
    checks: dict
    failure_type: str | None
    recovery_suggestion: str
    error: str | None


class VerifiedReplayResponse(BaseModel):
    replay_id: str
    compiled_skill_id: str
    status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    steps_verification_failed: int
    step_results: list[VerifiedStepResponse]
    finished_at: str


class VerificationEntryResponse(BaseModel):
    step_index: int
    step_id: str
    page_state_ok: bool
    record_identity_ok: bool
    selector_ambiguity_ok: bool
    modal_error_ok: bool
    post_state_ok: bool
    overall_status: str
    checks: dict


class VerificationResponse(BaseModel):
    replay_id: str
    verifications: list[VerificationEntryResponse]


class FailureEntryResponse(BaseModel):
    step_index: int
    step_id: str
    failure_type: str
    failure_detail: str
    recovery_suggestion: str
    severity: str


class FailuresResponse(BaseModel):
    replay_id: str
    failure_count: int
    failures: list[FailureEntryResponse]


class RobustReportResponse(BaseModel):
    replay_id: str
    compiled_skill_id: str
    target_base_url: str
    replay_status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    success_rate_pct: float
    llm_used_at_replay: bool
    deterministic: bool
    verification_count: int
    failure_count: int
    verifications: list[VerificationEntryResponse]
    failures: list[FailureEntryResponse]
    summary: str
    recovery_actions_required: bool
