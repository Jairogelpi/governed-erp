from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class OdooReadMappingRequest(BaseModel):
    requested_by: str = "operator_1"
    object_type: str = "sale_order"
    lookup: dict[str, Any] = Field(default_factory=dict)
    allow_business_read: bool = False


class OdooReadMappingResponse(BaseModel):
    read_mapping_id: str
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    object_type: str
    status: str
    allow_business_read: bool
    business_data_read: bool
    canonical_object: dict[str, Any]
    source_snapshot_redacted: dict[str, Any]
    field_allowlist_used: list[str]
    redacted_fields: list[str]
    external_http_performed: bool
    odoo_rpc_performed: bool
    odoo_read_performed: bool
    odoo_write_performed: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False
    blocking_reasons: list[str] = []


class OdooReadMappingListResponse(BaseModel):
    read_mappings: list[OdooReadMappingResponse]


class OdooReadMappingAuditEventResponse(BaseModel):
    event_type: str
    read_mapping_id: str
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    object_type: str
    status: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class OdooReadMappingAuditResponse(BaseModel):
    events: list[OdooReadMappingAuditEventResponse]
