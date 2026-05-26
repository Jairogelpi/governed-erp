from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DispatchExecuteRequest(BaseModel):
    plan_id: str
    step_number: int
    action_key: str
    endpoint_hint: str
    method_hint: str = "GET"
    token_id: str
    version_id: str | None = None
    parameters: dict[str, Any] = Field(default_factory=dict)


class DispatchResultResponse(BaseModel):
    dispatch_id: str
    action_key: str
    status: str
    dispatch_performed: bool
    handler_type: str
    token_confirmed: bool
    eligibility_passed: bool
    result_payload: dict[str, Any]
    result_summary: str
    blocking_reasons: list[str]
    erp_writes_performed: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    llm_runtime_used: bool = False
    system_state_mutated: bool = False
    skill_mutated: bool = False
    activation_performed: bool = False
    scheduling_performed: bool = False
    audit_recorded: bool = True
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class DispatchExecutionAuditEntrySchema(BaseModel):
    event_id: str
    dispatch_id: str
    action_key: str
    event_type: str
    status: str
    handler_type: str
    endpoint_hint: str
    method_hint: str
    token_id: str | None
    version_id: str | None
    detail: dict[str, Any]
    created_at: Any


class DispatchExecutionAuditResponse(BaseModel):
    entries: list[DispatchExecutionAuditEntrySchema]
    event_count: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class DispatchableActionsResponse(BaseModel):
    actions: list[str]
    total: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
