from __future__ import annotations

import hashlib
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.models import CredentialVaultEntry, CredentialVaultAuditEvent
from erpguard.db.repositories import (
    create_credential_vault_entry,
    get_credential_vault_entry_by_ref,
    revoke_credential_vault_entry,
    create_credential_vault_audit_event,
    list_credential_vault_audit_events,
    update_connector_setup_session,
    get_connector_setup_session,
)


class AuthType(StrEnum):
    PASSWORD = "password"
    API_KEY = "api_key"
    TOKEN = "token"
    OAUTH_PLACEHOLDER = "oauth_placeholder"
    UNKNOWN = "unknown"


class VaultEntryStatus(StrEnum):
    SEALED = "sealed"
    REVOKED = "revoked"
    BLOCKED = "blocked"


class CredentialVaultInput(BaseModel):
    setup_session_id: str
    auth_type: AuthType
    username: str | None = None
    password: str | None = None
    api_key: str | None = None
    token: str | None = None
    submitted_by: str


class CredentialVaultSealResult(BaseModel):
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


class CredentialVaultMetadataResult(BaseModel):
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


class CredentialVaultRevokeResult(BaseModel):
    credential_ref: str
    status: str
    raw_secret_returned: bool = False
    raw_secret_logged: bool = False


class CredentialVaultAuditResult(BaseModel):
    events: list[dict[str, Any]] = Field(default_factory=list)


def _fingerprint_secret(secret: str) -> str:
    normalized = secret.encode("utf-8")
    digest = hashlib.sha256(normalized).hexdigest()
    return f"sha256:{digest[:16]}"


def _redact_username(username: str | None) -> str | None:
    if not username:
        return None
    if "@" in username:
        local, domain = username.split("@", 1)
        if len(local) <= 2:
            return f"{local[0]}***@{domain}"
        return f"{local[0]}***@{domain}"
    if len(username) <= 3:
        return f"{username[0]}***"
    return f"{username[0]}***{username[-1]}"


def _extract_secret_last4(secret: str | None, auth_type: AuthType) -> str | None:
    if not secret:
        return None
    if auth_type == AuthType.PASSWORD:
        if len(secret) < 4:
            return "****"
        return secret[-4:]
    if auth_type == AuthType.API_KEY:
        if len(secret) < 4:
            return "****"
        return secret[-4:]
    if auth_type == AuthType.TOKEN:
        if len(secret) < 4:
            return "****"
        return secret[-4:]
    return None


def _get_secret_from_input(credential_input: CredentialVaultInput) -> str | None:
    auth_type = credential_input.auth_type
    if auth_type == AuthType.PASSWORD:
        return credential_input.password
    if auth_type == AuthType.API_KEY:
        return credential_input.api_key
    if auth_type == AuthType.TOKEN:
        return credential_input.token
    return None


class CredentialVaultContractService:
    def __init__(self, session: Session):
        self.session = session

    def seal_credential(self, credential_input: CredentialVaultInput) -> CredentialVaultSealResult:
        auth_type = credential_input.auth_type
        setup_session = get_connector_setup_session(self.session, credential_input.setup_session_id)

        if setup_session is None:
            return CredentialVaultSealResult(
                credential_ref="",
                setup_session_id=credential_input.setup_session_id,
                status="blocked",
                credential_stored=False,
                blocking_reasons=["setup_session_not_found"],
            )

        if setup_session.status == "blocked":
            return CredentialVaultSealResult(
                credential_ref="",
                setup_session_id=credential_input.setup_session_id,
                status="blocked",
                credential_stored=False,
                blocking_reasons=["setup_session_blocked"],
            )

        secret = _get_secret_from_input(credential_input)

        if auth_type in (AuthType.PASSWORD, AuthType.API_KEY, AuthType.TOKEN) and not secret:
            return CredentialVaultSealResult(
                credential_ref="",
                setup_session_id=credential_input.setup_session_id,
                status="blocked",
                credential_stored=False,
                blocking_reasons=["missing_secret"],
            )

        if auth_type not in (AuthType.PASSWORD, AuthType.API_KEY, AuthType.TOKEN, AuthType.OAUTH_PLACEHOLDER):
            return CredentialVaultSealResult(
                credential_ref="",
                setup_session_id=credential_input.setup_session_id,
                status="blocked",
                credential_stored=False,
                blocking_reasons=[f"unsupported_auth_type:{auth_type}"],
            )

        if secret and len(secret) < 1:
            return CredentialVaultSealResult(
                credential_ref="",
                setup_session_id=credential_input.setup_session_id,
                status="blocked",
                credential_stored=False,
                blocking_reasons=["weak_or_empty_secret"],
            )

        credential_ref = f"cred_{uuid4().hex[:20]}"
        secret_fingerprint = _fingerprint_secret(secret) if secret else "sha256:none"
        username_redacted = _redact_username(credential_input.username)
        secret_length = len(secret) if secret else None
        secret_last4 = _extract_secret_last4(secret, auth_type)

        entry = create_credential_vault_entry(
            self.session,
            credential_ref=credential_ref,
            setup_session_id=credential_input.setup_session_id,
            connector_name=setup_session.connector_name,
            erp_url_host=setup_session.erp_url_host,
            auth_type=auth_type.value,
            username_redacted=username_redacted,
            secret_fingerprint=secret_fingerprint,
            secret_length=secret_length,
            secret_last4=secret_last4,
            status="sealed",
            created_by=credential_input.submitted_by,
            blocking_reasons_json="[]",
        )

        update_connector_setup_session(
            self.session,
            setup_session.id,
            status="ready_for_fingerprint",
            credential_mode="vault_reference_only",
            credential_ref=credential_ref,
        )

        create_credential_vault_audit_event(
            self.session,
            credential_ref=credential_ref,
            setup_session_id=credential_input.setup_session_id,
            event_type="credential_sealed",
            auth_type=auth_type.value,
            status="sealed",
            username_redacted=username_redacted,
            secret_fingerprint=secret_fingerprint,
            created_by=credential_input.submitted_by,
            details_json="{}",
        )

        return CredentialVaultSealResult(
            credential_ref=credential_ref,
            setup_session_id=credential_input.setup_session_id,
            status="sealed",
            credential_stored=True,
            metadata={
                "auth_type": auth_type.value,
                "username_redacted": username_redacted,
                "secret_fingerprint": secret_fingerprint,
                "secret_last4": secret_last4,
            },
            blocking_reasons=[],
        )

    def get_metadata(self, credential_ref: str) -> CredentialVaultMetadataResult | None:
        entry = get_credential_vault_entry_by_ref(self.session, credential_ref)
        if entry is None:
            return None
        return CredentialVaultMetadataResult(
            credential_ref=entry.credential_ref,
            setup_session_id=entry.setup_session_id,
            connector_name=entry.connector_name,
            erp_url_host=entry.erp_url_host,
            auth_type=entry.auth_type,
            username_redacted=entry.username_redacted,
            secret_fingerprint=entry.secret_fingerprint,
            secret_length=entry.secret_length,
            secret_last4=entry.secret_last4,
            status=entry.status,
            created_at=entry.created_at.isoformat() if entry.created_at else None,
            revoked_at=entry.revoked_at.isoformat() if entry.revoked_at else None,
        )

    def revoke_credential(self, credential_ref: str, revoked_by: str) -> CredentialVaultRevokeResult:
        entry = get_credential_vault_entry_by_ref(self.session, credential_ref)
        if entry is None:
            return CredentialVaultRevokeResult(
                credential_ref=credential_ref,
                status="not_found",
            )

        revoke_credential_vault_entry(self.session, credential_ref)

        create_credential_vault_audit_event(
            self.session,
            credential_ref=credential_ref,
            setup_session_id=entry.setup_session_id,
            event_type="credential_revoked",
            auth_type=entry.auth_type,
            status="revoked",
            username_redacted=entry.username_redacted,
            secret_fingerprint=entry.secret_fingerprint,
            created_by=revoked_by,
            details_json="{}",
        )

        return CredentialVaultRevokeResult(
            credential_ref=credential_ref,
            status="revoked",
        )

    def get_audit(self, *, limit: int = 50) -> CredentialVaultAuditResult:
        events = list_credential_vault_audit_events(self.session, limit=limit)
        return CredentialVaultAuditResult(
            events=[
                {
                    "event_id": e.id,
                    "credential_ref": e.credential_ref,
                    "setup_session_id": e.setup_session_id,
                    "event_type": e.event_type,
                    "auth_type": e.auth_type,
                    "status": e.status,
                    "username_redacted": e.username_redacted,
                    "secret_fingerprint": e.secret_fingerprint,
                    "created_by": e.created_by,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in events
            ]
        )