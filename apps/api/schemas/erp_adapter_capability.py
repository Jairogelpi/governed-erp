from __future__ import annotations


from pydantic import BaseModel, Field


class ERPAdapterIdentitySchema(BaseModel):
    adapter_id: str
    adapter_type: str
    display_name: str
    vendor_name: str
    is_placeholder: bool
    supports_real_connection: bool


class ERPAdapterListResponse(BaseModel):
    adapters: list[ERPAdapterIdentitySchema]
    is_advisory_only: bool = True
    will_execute: bool = False
    can_execute: bool = False


class ERPAdapterCapabilitySchema(BaseModel):
    adapter_id: str
    adapter_type: str
    adapter_display_name: str
    operation_type: str
    object_type: str
    supported: bool
    safety_tier: str
    requires_credentials: bool
    requires_confirmed_token: bool
    supports_preview: bool
    supports_execution: bool
    supports_schema_inspection: bool
    supports_permission_inspection: bool
    field_read_allowlist: list[str]
    field_write_allowlist: list[str]
    blocking_reasons: list[str]


class ERPAdapterCapabilitiesResponse(BaseModel):
    adapter_id: str
    adapter_found: bool
    capabilities: list[ERPAdapterCapabilitySchema]
    blocking_reasons: list[str] = Field(default_factory=list)
    is_advisory_only: bool = True
    will_execute: bool = False
    can_execute: bool = False


class ERPAdapterCapabilityCheckRequestSchema(BaseModel):
    adapter_id: str
    operation_type: str
    object_type: str
    requested_fields: list[str] = Field(default_factory=list)


class ERPAdapterSafetyFlagsSchema(BaseModel):
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


class ERPAdapterCapabilityCheckResponse(BaseModel):
    adapter_id: str
    adapter_type: str
    adapter_display_name: str
    operation_type: str
    object_type: str
    supported: bool
    safety_tier: str
    requires_credentials: bool
    requires_confirmed_token: bool
    supports_preview: bool
    supports_execution: bool
    supports_schema_inspection: bool
    supports_permission_inspection: bool
    field_read_allowlist: list[str]
    field_write_allowlist: list[str]
    blocking_reasons: list[str]
    is_advisory_only: bool
    will_execute: bool
    can_execute: bool
    safety_flags: ERPAdapterSafetyFlagsSchema
