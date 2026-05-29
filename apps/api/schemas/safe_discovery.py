"""Sprint 57 - Safe Discovery Plan API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SafeDiscoveryPlanRequest(BaseModel):
    selected_adapter_type: str | None = None
    created_by: str = "operator_1"


class SafeDiscoveryPlanResponse(BaseModel):
    discovery_plan_id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    selected_adapter_type: str
    connector_name: str
    erp_url_host: str
    environment_type: str
    status: str
    read_only_surface: dict
    blocked_write_surface: list[dict]
    permission_surface: list[dict]
    planned_discovery_steps: list[dict]
    risk_summary: dict
    next_safe_step: str | None = None
    blocking_reasons: list[str] = Field(default_factory=list)
    will_connect: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    sample_data_read: bool = False
    capability_generation_performed: bool = False
    read_only_activation_performed: bool = False
    erp_write_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


class SafeDiscoveryPlanListItem(BaseModel):
    discovery_plan_id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    selected_adapter_type: str
    connector_name: str
    erp_url_host: str
    status: str


class SafeDiscoveryPlanListResponse(BaseModel):
    plans: list[SafeDiscoveryPlanListItem]


class SafeDiscoveryAuditEventResponse(BaseModel):
    id: str
    discovery_plan_id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    event_type: str
    status: str
    created_by: str
    details: str
    created_at: str


class SafeDiscoveryAuditResponse(BaseModel):
    events: list[SafeDiscoveryAuditEventResponse]
