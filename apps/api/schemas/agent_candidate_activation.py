from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ActivationRequestBody(BaseModel):
    actor: str = "system"


class ActivationCheckSchema(BaseModel):
    check: str
    passed: bool
    detail: str


class CandidateActivationEligibilityResponse(BaseModel):
    version_id: str
    skill_id: str
    eligible: bool
    checks: list[ActivationCheckSchema]
    blocking_reasons: list[str]
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool


class CandidateActivationResponse(BaseModel):
    version_id: str
    skill_id: str
    activated: bool
    prior_version_deactivated: bool
    prior_version_id: str
    version_status: str
    is_active: bool
    is_executed: bool
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class CandidateActivationStatusResponse(BaseModel):
    version_id: str
    skill_id: str
    version_status: str
    is_active: bool
    latest_decision: str | None
    request_id: str
    request_status: str
    event_count: int
    is_executed: bool
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool


class ActivationAuditEntrySchema(BaseModel):
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: datetime
    source: str


class CandidateActivationAuditResponse(BaseModel):
    version_id: str
    skill_id: str
    event_count: int
    lifecycle_event_count: int
    entries: list[ActivationAuditEntrySchema]
    can_execute: bool
    is_advisory_only: bool


class PostActivationSummaryResponse(BaseModel):
    version_id: str
    skill_id: str
    version_status: str
    runtime_type: str
    is_active: bool
    latest_decision: str | None
    governance_status: str
    request_id: str
    request_status: str
    activation_event_count: int
    lifecycle_event_count: int
    summary_notes: list[str]
    is_executed: bool
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
