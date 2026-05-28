from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CredentialSealRequest(BaseModel):
    setup_session_id: str
    auth_type: str
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    token: str | None = None
    submitted_by: str


class CredentialSealResponse(BaseModel):
    credential_ref: str
    setup_session_id: str
    status: str
    credential_stored: bool = True
    raw_secret_returned: bool = False
    raw_secret_logged: bool = False
    llm_accessible: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    fingerprint_performed: bool = False
    schema_inspection_performed: bool = False
    capability_generation_performed: bool = False
    read_only_activation_performed: bool = False
    erp_write_performed: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)
    blocking_reasons: list[str] = Field(default_factory=list)


class CredentialMetadataResponse(BaseModel):
    credential_ref: str
    setup_session_id: str
    connector_name: str
    erp_url_host: str
    auth_type: str
    username_redacted: str | None = None
    secret_fingerprint: str
    secret_length: int | None = None
    secret_last4: str | None = None
    status: str
    created_at: str | None = None
    revoked_at: str | None = None


class CredentialRevokeResponse(BaseModel):
    credential_ref: str
    status: str
    raw_secret_returned: bool = False
    raw_secret_logged: bool = False


class CredentialAuditResponse(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)
