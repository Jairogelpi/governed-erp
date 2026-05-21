from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateTenantBody(BaseModel):
    name: str
    environment: str = "staging"


class KillSwitchBody(BaseModel):
    switch_name: str
    action: str
    activated_by: dict[str, Any]
    reason: str


class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    environment: str
    status: str
    kill_switches: dict[str, bool]
    rate_limits: dict[str, Any]
    roles: list[dict[str, Any]]
    secret_redaction_enforced: bool
    created_at: str | None = None
    updated_at: str | None = None


class KillSwitchEventResponse(BaseModel):
    event_id: str
    tenant_id: str
    switch_name: str
    action: str
    activated_by: dict[str, Any]
    reason: str
    created_at: str | None = None


class TenantSafetySummaryResponse(BaseModel):
    tenant_id: str
    tenant_name: str
    environment: str
    status: str
    kill_switches: dict[str, bool]
    any_kill_switch_active: bool
    rate_limits: dict[str, Any]
    secret_redaction_enforced: bool
    recent_kill_switch_events: int
    allow_generic_real_odoo_writes: bool = False
    allow_r3_r4_real_writes: bool = False


class AuditExportBody(BaseModel):
    filters: dict[str, Any] = {}


class AuditExportResponse(BaseModel):
    export_id: str
    tenant_id: str
    export_type: str
    filters: dict[str, Any]
    record_count: int
    status: str
    result: list[dict[str, Any]]
    created_at: str | None = None
    completed_at: str | None = None


class PolicyEvaluationBody(BaseModel):
    actor: dict[str, Any]
    action: str
    resource: str
    context: dict[str, Any] = {}
    tenant_id: str | None = None


class PolicyEvaluationResponse(BaseModel):
    allowed: bool
    actor: dict[str, Any]
    action: str
    resource: str
    reason: str
    violations: list[str]
    kill_switches_active: list[str]
    allow_generic_real_odoo_writes: bool = False
    allow_r3_r4_real_writes: bool = False


class RuntimeSafetyResponse(BaseModel):
    platform_global_kill_switch: bool
    runtime_execution_kill_switch: bool
    write_pilot_kill_switch: bool
    tenant_controls_enabled: bool
    environment_guard_enabled: bool
    audit_export_enabled: bool
    rate_limits_enabled: bool
    secret_redaction_enforced: bool
    allow_r1_real_write_pilot: bool
    allow_generic_real_odoo_writes: bool
    allow_r3_r4_real_writes: bool
    active_tenant_count: int
    recent_write_pilot_runs: int
    safety_level: str
