from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


SENSITIVE_RAW_CREDENTIAL_KEYS = {
    "password",
    "api_key",
    "token",
    "secret",
    "credential",
    "credentials",
}


class ConnectorSetupSessionCreateRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    connector_name: str = Field(min_length=1)
    erp_url: str = Field(min_length=1)
    environment_type: Literal["sandbox", "staging", "production", "unknown"] = "unknown"
    submitted_by: str = Field(min_length=1)
    credential_ref: str | None = None

    def raw_credentials_seen(self) -> bool:
        return _contains_sensitive_key(self.model_extra or {})


class ConnectorSetupSessionResponse(BaseModel):
    session_id: str
    connector_name: str
    erp_url: str
    erp_url_host: str
    environment_type: str
    submitted_by: str
    status: str
    credential_mode: str
    credential_ref: str | None = None
    detected_adapter_type: str | None = None
    requires_credentials: bool
    can_fingerprint: bool
    can_activate_read_only: bool
    will_connect: bool
    external_http_performed: bool
    credentials_stored: bool
    raw_credentials_seen: bool
    login_attempted: bool
    fingerprint_performed: bool
    schema_inspection_performed: bool
    capability_generation_performed: bool
    read_only_activation_performed: bool
    erp_write_performed: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    audit_recorded: bool
    created_at: str | None = None
    updated_at: str | None = None


class ConnectorSetupSessionListResponse(BaseModel):
    sessions: list[ConnectorSetupSessionResponse] = Field(default_factory=list)
    will_connect: bool = False
    external_http_performed: bool = False
    raw_credentials_seen: bool = False
    credentials_stored: bool = False
    login_attempted: bool = False
    fingerprint_performed: bool = False
    schema_inspection_performed: bool = False
    capability_generation_performed: bool = False
    read_only_activation_performed: bool = False
    erp_write_performed: bool = False


class ConnectorSetupAuditEventResponse(BaseModel):
    event_id: str
    session_id: str
    event_type: str
    status: str
    submitted_by: str
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ConnectorSetupAuditResponse(BaseModel):
    events: list[ConnectorSetupAuditEventResponse] = Field(default_factory=list)
    event_count: int


def _contains_sensitive_key(value: Any) -> bool:
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_RAW_CREDENTIAL_KEYS:
                return True
            if _contains_sensitive_key(item):
                return True
    if isinstance(value, list):
        return any(_contains_sensitive_key(item) for item in value)
    return False
