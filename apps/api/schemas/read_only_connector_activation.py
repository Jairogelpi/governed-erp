"""Sprint 59 - read-only connector activation API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReadOnlyActivationRequestCreate(BaseModel):
    requested_by: str = "operator_1"
    mode: str = "read_only"


class ReadOnlyActivationApproveRequest(BaseModel):
    approved_by: str


class ReadOnlyActivationRequestResponse(BaseModel):
    activation_request_id: str
    capability_set_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    mode: str
    requested_by: str
    status: str
    requires_human_approval: bool = True
    blocking_reasons: list[str] = Field(default_factory=list)
    will_connect: bool = False
    can_read_real_erp: bool = False
    can_write_real_erp: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    real_erp_connection_established: bool = False
    real_erp_read_enabled: bool = False
    real_erp_write_enabled: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    scheduler_used: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


class ReadOnlyActivationResponse(BaseModel):
    activation_id: str
    activation_request_id: str
    capability_set_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    mode: str
    status: str
    approved_by: str
    blocking_reasons: list[str] = Field(default_factory=list)
    external_http_performed: bool = False
    login_attempted: bool = False
    real_erp_connection_established: bool = False
    real_erp_read_enabled: bool = False
    real_erp_write_enabled: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    scheduler_used: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


class ReadOnlyActivationListResponse(BaseModel):
    activations: list[ReadOnlyActivationResponse]


class ReadOnlyActivationAuditEventResponse(BaseModel):
    id: str
    activation_request_id: str
    activation_id: str
    capability_set_id: str
    setup_session_id: str
    credential_ref: str
    event_type: str
    status: str
    actor: str
    details: str
    created_at: str


class ReadOnlyActivationAuditResponse(BaseModel):
    events: list[ReadOnlyActivationAuditEventResponse]
