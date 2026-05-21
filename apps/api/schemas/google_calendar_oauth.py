from __future__ import annotations

from pydantic import BaseModel


class AuthorizeRequest(BaseModel):
    profile_id: str
    redirect_uri: str | None = None
    actor: dict = {}


class AuthorizeResponse(BaseModel):
    authorization_url: str
    state_token: str
    profile_id: str
    scope_requested: str
    redirect_uri: str
    placeholder_mode: bool
    token_exposed: bool
    secret_redacted: bool


class CallbackResponse(BaseModel):
    profile_id: str
    connector_id: str
    vault_ref: str
    secret_fingerprint: str
    scope_granted: list[str]
    scope_compliant: bool
    has_refresh_token: bool
    placeholder_mode: bool
    token_exposed: bool
    secret_redacted: bool
    token_record_id: str


class OAuthStatusResponse(BaseModel):
    profile_id: str
    connector_id: str
    authorized: bool
    scope_compliant: bool
    scope_granted: list[str]
    placeholder_mode: bool
    token_record_id: str
    status: str
    token_exposed: bool
    secret_redacted: bool


class ScopeVerificationResponse(BaseModel):
    profile_id: str
    scope_compliant: bool
    scope_granted: list[str]
    allowed_scope: str
    violations: list[str]
    token_exposed: bool


class RevokeRequest(BaseModel):
    actor: dict = {}


class RevokeResponse(BaseModel):
    profile_id: str
    revoked: bool
    placeholder_mode: bool
    token_exposed: bool
    secret_redacted: bool
