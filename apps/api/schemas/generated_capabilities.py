"""Sprint 58 - generated capabilities API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class GeneratedCapabilityRequest(BaseModel):
    created_by: str = "operator_1"


class GeneratedCapabilitySetResponse(BaseModel):
    capability_set_id: str
    discovery_plan_id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    status: str
    capabilities: list[dict]
    blocked_capabilities: list[dict]
    source_surface_snapshot: dict
    policy_summary: dict
    blocking_reasons: list[str] = Field(default_factory=list)
    is_advisory_only: bool = True
    will_execute: bool = False
    can_execute: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    sample_data_read: bool = False
    capability_generation_performed: bool = True
    read_only_activation_performed: bool = False
    erp_write_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


class GeneratedCapabilitySetListItem(BaseModel):
    capability_set_id: str
    discovery_plan_id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    status: str


class GeneratedCapabilitySetListResponse(BaseModel):
    capability_sets: list[GeneratedCapabilitySetListItem]


class GeneratedCapabilityAuditEventResponse(BaseModel):
    id: str
    capability_set_id: str
    discovery_plan_id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    event_type: str
    status: str
    created_by: str
    details: str
    created_at: str


class GeneratedCapabilityAuditResponse(BaseModel):
    events: list[GeneratedCapabilityAuditEventResponse]
