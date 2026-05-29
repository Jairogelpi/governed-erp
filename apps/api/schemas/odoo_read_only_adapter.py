"""Sprint 74 - Odoo read-only adapter shell schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class OdooReadOnlyAdapterSessionRequest(BaseModel):
    created_by: str = "operator_1"


class OdooReadOnlyAdapterSessionResponse(BaseModel):
    adapter_session_id: str
    activation_id: str
    capability_set_id: str
    setup_session_id: str
    credential_ref: str
    adapter_id: str
    adapter_type: str
    mode: str
    status: str
    created_by: str
    blocking_reasons: list[str] = Field(default_factory=list)
    can_connect_later: bool = False
    will_connect_now: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    odoo_rpc_performed: bool = False
    odoo_read_performed: bool = False
    odoo_write_performed: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


class OdooReadOnlyAdapterSessionListResponse(BaseModel):
    sessions: list[OdooReadOnlyAdapterSessionResponse]


class OdooReadOnlyAdapterAuditEventResponse(BaseModel):
    id: str
    adapter_session_id: str
    activation_id: str
    capability_set_id: str
    setup_session_id: str
    credential_ref: str
    event_type: str
    status: str
    actor: str
    details: str
    created_at: str


class OdooReadOnlyAdapterAuditResponse(BaseModel):
    events: list[OdooReadOnlyAdapterAuditEventResponse]
