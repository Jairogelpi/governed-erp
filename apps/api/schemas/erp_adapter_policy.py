from __future__ import annotations

from pydantic import BaseModel, Field


class ERPAdapterPolicyCheckRequestSchema(BaseModel):
    adapter_id: str
    operation_type: str
    object_type: str
    requested_fields: list[str] = Field(default_factory=list)
    actor: str | None = None
    has_confirmed_token: bool = False
    has_credentials: bool = False
    phase: str = "block_c_contract_only"


class ERPAdapterPolicySafetyFlagsSchema(BaseModel):
    real_erp_touched: bool
    real_erp_write_performed: bool
    external_http_performed: bool
    credentials_used: bool
    browser_control_performed: bool
    mcp_execution_performed: bool
    scheduler_used: bool
    endpoint_hint_executed: bool
    llm_runtime_used: bool
    odoo_touched: bool
    sap_touched: bool
    dynamics_touched: bool
    netsuite_touched: bool


class ERPAdapterPolicyCheckResponse(BaseModel):
    eligible: bool
    adapter_id: str
    adapter_type: str
    adapter_display_name: str
    operation_type: str
    object_type: str
    safety_tier: str
    capability_supported: bool
    requires_confirmation: bool
    requires_credentials: bool
    can_preview: bool
    can_execute: bool
    policy_phase: str
    blocking_reasons: list[str]
    is_advisory_only: bool
    will_execute: bool
    safety_flags: ERPAdapterPolicySafetyFlagsSchema
