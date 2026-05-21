from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


MANDATORY_GUARDS = ["no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review"]
ODOO_FORMULA_GUARDS = ["formula_guard", "odoo_readonly_guard"]
WRITE_PILOT_GUARDS = ["write_readiness_required", "approval_required", "idempotency_required", "snapshot_required", "rollback_required"]


class AgentBuilderSafety(BaseModel):
    generic_writes_enabled: bool = False
    r3_r4_writes_enabled: bool = False
    freeform_tool_execution_enabled: bool = False
    can_execute_real_writes: bool = False
    requires_review: bool = True
    requires_compile: bool = True
    requires_approval: bool = True


class AgentBuilderSessionModel(BaseModel):
    session_id: str
    status: str
    next_step: str
    template_id: str | None = None
    connector_id: str | None = None
    trigger: dict[str, Any] = Field(default_factory=dict)
    inputs: dict[str, Any] = Field(default_factory=dict)
    outputs: dict[str, Any] = Field(default_factory=dict)
    steps: list[dict[str, Any]] = Field(default_factory=list)
    guards: list[str] = Field(default_factory=list)
    requirement_result: dict[str, Any] = Field(default_factory=dict)
    safety_preview: dict[str, Any] = Field(default_factory=dict)
    automation_draft_id: str | None = None
    created_by: dict[str, Any] = Field(default_factory=dict)
    safety: AgentBuilderSafety = Field(default_factory=AgentBuilderSafety)
    created_at: str | None = None
    updated_at: str | None = None


class AgentBuilderEventModel(BaseModel):
    event_id: str
    session_id: str
    event_type: str
    status: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    error: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class AgentBuilderValidationIssue(BaseModel):
    code: str
    message: str
    severity: str = "blocking"


class AgentBuilderValidationResult(BaseModel):
    session_id: str
    passed: bool
    issues: list[AgentBuilderValidationIssue] = Field(default_factory=list)
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    requires_review: bool = True
    requires_compile: bool = True
    requires_approval: bool = True


class AgentBuilderPreviewModel(BaseModel):
    session_id: str
    status: str
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    workflow: dict[str, Any] = Field(default_factory=dict)
    safety: AgentBuilderSafety = Field(default_factory=AgentBuilderSafety)


class AgentBuilderSaveDraftResult(BaseModel):
    session_id: str
    status: str
    automation_draft_id: str
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    next_step: str = "review_draft"
    safety: AgentBuilderSafety = Field(default_factory=AgentBuilderSafety)
