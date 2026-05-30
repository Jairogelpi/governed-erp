from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class OdooConnectionTestRequest(BaseModel):
    requested_by: str = "operator_1"
    allow_network_test: bool = False


class OdooConnectionTestResponse(BaseModel):
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    adapter_type: str = "odoo"
    status: str
    network_test_allowed: bool
    external_http_performed: bool
    login_attempted: bool
    login_succeeded: bool
    odoo_rpc_performed: bool
    odoo_server_version: str | None = None
    business_data_read: bool = False
    schema_inspection_performed: bool = False
    permission_inspection_performed: bool = False
    odoo_write_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False
    blocking_reasons: list[str] = []


class OdooConnectionTestListResponse(BaseModel):
    connection_tests: list[OdooConnectionTestResponse]


class OdooConnectionTestAuditEventResponse(BaseModel):
    event_type: str
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    status: str
    actor: str
    details: dict
    created_at: datetime


class OdooConnectionTestAuditResponse(BaseModel):
    events: list[OdooConnectionTestAuditEventResponse]
