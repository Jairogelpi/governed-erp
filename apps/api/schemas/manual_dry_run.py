from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ActorSchema(BaseModel):
    type: str
    id: str
    display_name: str | None = None


class ManualDryRunRequest(BaseModel):
    version_id: str
    token_id: str
    actor: ActorSchema
    source_plan_id: str | None = None
    source_step_number: int | None = None
    mode: str = "dry_run"
    inputs: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None
    requested_target: str | None = "simulation"


class ManualDryRunResponse(BaseModel):
    run_id: str
    version_id: str
    status: str
    mode: str
    execution_performed: bool
    simulation_performed: bool
    erp_writes_performed: bool
    browser_control_performed: bool
    mcp_execution_performed: bool
    llm_runtime_used: bool
    scheduler_used: bool
    active_skill_run_created: bool
    fake_erp_execution_performed: bool
    odoo_execution_performed: bool
    evidence_id: str | None
    audit_recorded: bool
    result_summary: str
    blocking_reasons: list[str]
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


class ManualDryRunAuditEntry(BaseModel):
    event_id: str
    run_id: str
    version_id: str
    actor: dict[str, Any]
    event_type: str
    status: str
    detail: dict[str, Any]
    created_at: Any


class ManualDryRunAuditResponse(BaseModel):
    entries: list[ManualDryRunAuditEntry]
    event_count: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
