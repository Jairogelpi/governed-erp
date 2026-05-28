from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FakeERPRegressionActorSchema(BaseModel):
    type: str
    id: str
    display_name: str | None = None


class FakeERPRegressionCaseRequest(BaseModel):
    version_id: str
    dry_run_id: str
    name: str
    execution_target: str = "fake_erp"
    inputs: dict[str, Any] = Field(default_factory=dict)
    expected_outcomes: dict[str, Any] = Field(default_factory=dict)


class FakeERPRegressionCaseResponse(BaseModel):
    case_id: str
    version_id: str
    dry_run_id: str
    name: str
    execution_target: str
    inputs: dict[str, Any]
    expected_outcomes: dict[str, Any]
    created: bool
    blocking_reasons: list[str]


class FakeERPRegressionRunRequest(BaseModel):
    case_id: str
    token_id: str
    actor: FakeERPRegressionActorSchema
    reason: str | None = None


class FakeERPRegressionRunResponse(BaseModel):
    regression_run_id: str
    case_id: str
    version_id: str
    dry_run_id: str
    execution_id: str | None
    evidence_pack_id: str | None
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
    comparison_summary: dict[str, Any]
    matched: bool
    audit_recorded: bool
    result_summary: str
    blocking_reasons: list[str]


class FakeERPRegressionAuditEntrySchema(BaseModel):
    event_id: str
    regression_run_id: str
    case_id: str
    version_id: str
    execution_id: str | None
    evidence_pack_id: str | None
    actor: dict[str, Any]
    event_type: str
    status: str
    detail: dict[str, Any]
    created_at: Any


class FakeERPRegressionAuditResponse(BaseModel):
    entries: list[FakeERPRegressionAuditEntrySchema]
    event_count: int
