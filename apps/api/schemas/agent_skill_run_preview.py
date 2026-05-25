from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class RunPreviewCheckSchema(BaseModel):
    check: str
    passed: bool
    detail: str


class RunPreviewEligibilityResponse(BaseModel):
    version_id: str
    skill_id: str
    eligible: bool
    checks: list[RunPreviewCheckSchema]
    blocking_reasons: list[str]
    will_execute: bool
    can_execute: bool
    is_advisory_only: bool


class RunPlanStepSchema(BaseModel):
    step_index: int
    step_id: str
    step_type: str
    description: str
    guard_check: str
    will_execute: bool
    estimated_impact: str


class RunPlanResponse(BaseModel):
    version_id: str
    skill_id: str
    plan_ready: bool
    step_count: int
    steps: list[RunPlanStepSchema]
    guard_names: list[str]
    runtime_type: str
    plan_is_dry_run: bool
    will_execute: bool
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str


class ExecutionGateCheckSchema(BaseModel):
    check: str
    passed: bool
    detail: str


class ExecutionGateResponse(BaseModel):
    version_id: str
    skill_id: str
    gate_passed: bool
    execution_ready: bool
    checks: list[ExecutionGateCheckSchema]
    blocking_reasons: list[str]
    will_execute: bool
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str


class RunPreviewResponse(BaseModel):
    version_id: str
    skill_id: str
    preview_ready: bool
    eligible: bool
    plan_ready: bool
    gate_passed: bool
    execution_ready: bool
    step_count: int
    runtime_type: str
    guard_names: list[str]
    will_execute: bool
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str


class PreviewAuditEventSchema(BaseModel):
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: datetime


class RunPreviewAuditResponse(BaseModel):
    version_id: str
    skill_id: str
    event_count: int
    events: list[PreviewAuditEventSchema]
    will_execute: bool
    can_execute: bool
    is_advisory_only: bool
