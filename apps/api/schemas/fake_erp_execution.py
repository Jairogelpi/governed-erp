from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FakeERPExecutionActorSchema(BaseModel):
    type: str
    id: str
    display_name: str | None = None


class FakeERPExecutionRequest(BaseModel):
    version_id: str
    dry_run_id: str
    token_id: str
    actor: FakeERPExecutionActorSchema
    execution_target: str = "fake_erp"
    inputs: dict[str, Any] = Field(default_factory=dict)
    reason: str | None = None


class FakeERPExecutionResponse(BaseModel):
    execution_id: str
    version_id: str
    dry_run_id: str
    status: str
    execution_target: str
    execution_performed: bool
    fake_erp_execution_performed: bool
    odoo_execution_performed: bool
    real_erp_execution_performed: bool
    erp_writes_performed: bool
    browser_control_performed: bool
    mcp_execution_performed: bool
    llm_runtime_used: bool
    scheduler_used: bool
    external_http_performed: bool
    steps_executed: int
    steps_blocked: int
    evidence_pack_id: str | None
    audit_recorded: bool
    result_summary: str
    blocking_reasons: list[str]


class FakeERPExecutionAuditEntrySchema(BaseModel):
    event_id: str
    execution_id: str
    version_id: str
    dry_run_id: str
    actor: dict[str, Any]
    event_type: str
    status: str
    detail: dict[str, Any]
    created_at: Any


class FakeERPExecutionAuditResponse(BaseModel):
    entries: list[FakeERPExecutionAuditEntrySchema]
    event_count: int
