from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActionPlanRequest(BaseModel):
    goal: str
    version_id: str | None = None
    actor: str = "operator"


class ActionPlanStepSchema(BaseModel):
    step_number: int
    title: str
    description: str
    endpoint_hint: str
    method_hint: str
    severity: str
    prereqs_met: bool
    blocker_reason: str | None
    requires_operator_click: bool = True
    executable: bool = False


class ActionPlanResponse(BaseModel):
    plan_id: str
    plan_type: str
    goal: str
    version_id: str | None
    steps: list[ActionPlanStepSchema]
    total_steps: int
    blocking_count: int
    advisory_summary: str
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class ActionPlanAuditEntrySchema(BaseModel):
    plan_id: str
    plan_type: str
    goal: str
    version_id_context: str | None
    step_count: int
    blocking_count: int
    created_at: Any


class ActionPlanAuditResponse(BaseModel):
    entries: list[ActionPlanAuditEntrySchema]
    event_count: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class SupportedPlanTypeSchema(BaseModel):
    plan_type: str
    description: str


class SupportedPlanTypesResponse(BaseModel):
    plan_types: list[SupportedPlanTypeSchema]
    total: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
