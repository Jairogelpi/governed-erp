from __future__ import annotations

from pydantic import BaseModel, Field


class BridgeEligibilityIssueSchema(BaseModel):
    code: str
    message: str
    severity: str


class BridgeEligibilityResponse(BaseModel):
    draft_id: str
    eligible: bool
    is_agent_draft: bool
    proposal_id: str | None = None
    issues: list[BridgeEligibilityIssueSchema] = Field(default_factory=list)
    runtime_mode: str
    write_actions: bool
    can_execute: bool
    is_advisory_only: bool


class ClarificationGateResponse(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    gate_passed: bool
    questions_pct: int
    mappings_pct: int
    overall_complete: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    can_execute: bool
    is_advisory_only: bool


class DraftReviewBridgeResponse(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    review_id: str | None = None
    bridged: bool
    review_status: str | None = None
    guards_count: int
    test_cases_count: int
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str | None = None


class ValidationBridgeIssueSchema(BaseModel):
    code: str
    message: str
    severity: str


class DraftValidationBridgeResponse(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    validation_passed: bool
    issues: list[ValidationBridgeIssueSchema] = Field(default_factory=list)
    guard_normalization_applied: bool
    can_execute: bool
    is_advisory_only: bool


class CompilePlanStepSchema(BaseModel):
    step_id: str
    description: str
    status: str


class DraftCompileBridgeResponse(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    plan_generated: bool
    plan_steps: list[CompilePlanStepSchema] = Field(default_factory=list)
    estimated_inputs: list[str] = Field(default_factory=list)
    estimated_outputs: list[str] = Field(default_factory=list)
    compile_blocked: bool
    blocking_reason: str | None = None
    can_execute: bool
    is_advisory_only: bool
    safety_note: str


class BridgeStepStatusSchema(BaseModel):
    step: str
    status: str
    detail: str | None = None


class DraftBridgeReportResponse(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    overall_status: str
    steps: list[BridgeStepStatusSchema] = Field(default_factory=list)
    can_execute: bool
    is_advisory_only: bool
    next_action: str


class BridgeAuditEntrySchema(BaseModel):
    event_id: str
    step: str
    status: str
    detail: dict
    created_at: str


class DraftBridgeAuditResponse(BaseModel):
    draft_id: str
    event_count: int
    events: list[BridgeAuditEntrySchema] = Field(default_factory=list)
    can_execute: bool
    is_advisory_only: bool
