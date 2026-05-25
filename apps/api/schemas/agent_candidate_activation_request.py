from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class ActivationRequestBody(BaseModel):
    requested_by: str
    rationale: str = ""


class EligibilityCheckSchema(BaseModel):
    check: str
    passed: bool
    detail: str


class ActivationRequestEligibilityResponse(BaseModel):
    version_id: str
    skill_id: str
    eligible: bool
    checks: list[EligibilityCheckSchema]
    blocking_reasons: list[str]
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool


class ActivationRequestResponse(BaseModel):
    version_id: str
    skill_id: str
    request_id: str
    request_status: str
    requested_by: str
    rationale: str
    eligible: bool
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class ActivationRequestStatusResponse(BaseModel):
    version_id: str
    skill_id: str
    request_id: str
    request_status: str
    requested_by: str
    rationale: str
    event_count: int
    latest_decision: str | None
    version_status: str
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool


class FinalGateCheckSchema(BaseModel):
    check: str
    passed: bool
    detail: str


class FinalActivationGateResponse(BaseModel):
    version_id: str
    skill_id: str
    gate_passed: bool
    activation_allowed: bool
    checks: list[FinalGateCheckSchema]
    blocking_reasons: list[str]
    request_id: str
    request_status: str
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class ActivationRequestAuditEventSchema(BaseModel):
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: datetime


class ActivationRequestAuditResponse(BaseModel):
    version_id: str
    skill_id: str
    event_count: int
    events: list[ActivationRequestAuditEventSchema]
    can_execute: bool
    is_advisory_only: bool
