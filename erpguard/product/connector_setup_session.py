from __future__ import annotations

import json
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_connector_setup_session,
    get_connector_setup_session,
    list_connector_setup_sessions,
)
from erpguard.product.connector_setup_audit import ConnectorSetupAuditService


class ConnectorSetupEnvironmentType(StrEnum):
    SANDBOX = "sandbox"
    STAGING = "staging"
    PRODUCTION = "production"
    UNKNOWN = "unknown"


class ConnectorSetupStatus(StrEnum):
    DRAFT = "draft"
    AWAITING_CREDENTIALS = "awaiting_credentials"
    READY_FOR_FINGERPRINT = "ready_for_fingerprint"
    BLOCKED = "blocked"


class ConnectorSetupCredentialMode(StrEnum):
    NOT_PROVIDED = "not_provided"
    PENDING_VAULT = "pending_vault"
    VAULT_REFERENCE_ONLY = "vault_reference_only"


class ConnectorSetupInput(BaseModel):
    connector_name: str
    erp_url: str
    environment_type: ConnectorSetupEnvironmentType = ConnectorSetupEnvironmentType.UNKNOWN
    submitted_by: str
    credential_ref: str | None = None
    raw_credentials_seen: bool = False


class ConnectorSetupSession(BaseModel):
    session_id: str
    connector_name: str
    erp_url: str
    erp_url_host: str
    environment_type: ConnectorSetupEnvironmentType
    submitted_by: str
    status: ConnectorSetupStatus
    credential_mode: ConnectorSetupCredentialMode
    credential_ref: str | None = None
    detected_adapter_type: str | None = None
    requires_credentials: bool
    can_fingerprint: bool = False
    can_activate_read_only: bool = False
    will_connect: bool = False
    external_http_performed: bool = False
    credentials_stored: bool = False
    raw_credentials_seen: bool = False
    login_attempted: bool = False
    fingerprint_performed: bool = False
    schema_inspection_performed: bool = False
    capability_generation_performed: bool = False
    read_only_activation_performed: bool = False
    erp_write_performed: bool = False
    blocking_reasons: list[str] = Field(default_factory=list)
    audit_recorded: bool = True
    created_at: str | None = None
    updated_at: str | None = None


class ConnectorSetupSessionList(BaseModel):
    sessions: list[ConnectorSetupSession] = Field(default_factory=list)
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


class ConnectorSetupService:
    def __init__(self, session: Session):
        self.session = session
        self.audit = ConnectorSetupAuditService(session)

    def create_session(self, setup_input: ConnectorSetupInput) -> ConnectorSetupSession:
        session_id = f"csess_{uuid4().hex[:16]}"
        submitted_by = setup_input.submitted_by.strip() or "operator"
        connector_name = setup_input.connector_name.strip()
        erp_url = setup_input.erp_url.strip()

        self.audit.record(
            session_id=session_id,
            event_type="setup_session_requested",
            status=ConnectorSetupStatus.DRAFT.value,
            submitted_by=submitted_by,
            detail={
                "connector_name": connector_name,
                "environment_type": setup_input.environment_type.value,
                "credential_ref_provided": bool(setup_input.credential_ref),
                "raw_credentials_seen": setup_input.raw_credentials_seen,
                "will_connect": False,
                "external_http_performed": False,
            },
        )

        erp_url_host, url_blocking_reasons = normalize_erp_url_host(erp_url)
        blocking_reasons = list(url_blocking_reasons)
        if setup_input.raw_credentials_seen:
            blocking_reasons.append("raw_credentials_not_allowed_in_sprint_54")

        credential_ref = _normalize_optional_ref(setup_input.credential_ref)
        if blocking_reasons:
            status = ConnectorSetupStatus.BLOCKED
        elif credential_ref:
            status = ConnectorSetupStatus.READY_FOR_FINGERPRINT
        else:
            status = ConnectorSetupStatus.AWAITING_CREDENTIALS

        credential_mode = (
            ConnectorSetupCredentialMode.VAULT_REFERENCE_ONLY
            if credential_ref and status != ConnectorSetupStatus.BLOCKED
            else ConnectorSetupCredentialMode.NOT_PROVIDED
        )

        row = create_connector_setup_session(
            self.session,
            session_id=session_id,
            connector_name=connector_name,
            erp_url=erp_url,
            erp_url_host=erp_url_host,
            environment_type=setup_input.environment_type.value,
            submitted_by=submitted_by,
            status=status.value,
            credential_mode=credential_mode.value,
            credential_ref=credential_ref if status != ConnectorSetupStatus.BLOCKED else None,
            detected_adapter_type=None,
            blocking_reasons_json=json.dumps(blocking_reasons),
        )
        event_type = (
            "setup_session_blocked"
            if status == ConnectorSetupStatus.BLOCKED
            else "setup_session_created"
        )
        self.audit.record(
            session_id=session_id,
            event_type=event_type,
            status=status.value,
            submitted_by=submitted_by,
            detail={
                "erp_url_host": erp_url_host,
                "blocking_reasons": blocking_reasons,
                "credential_mode": credential_mode.value,
                "will_connect": False,
                "external_http_performed": False,
                "credentials_stored": False,
                "raw_credentials_seen": setup_input.raw_credentials_seen,
            },
        )
        return self._model(row)

    def get_session(self, session_id: str) -> ConnectorSetupSession:
        row = get_connector_setup_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Connector setup session '{session_id}' was not found.")
        return self._model(row)

    def list_sessions(self) -> ConnectorSetupSessionList:
        sessions = [self._model(row) for row in list_connector_setup_sessions(self.session)]
        return ConnectorSetupSessionList(
            sessions=sessions,
            raw_credentials_seen=any(item.raw_credentials_seen for item in sessions),
        )

    def _model(self, row) -> ConnectorSetupSession:
        blocking_reasons = _from_json(row.blocking_reasons_json, [])
        raw_credentials_seen = "raw_credentials_not_allowed_in_sprint_54" in blocking_reasons
        requires_credentials = not bool(row.credential_ref)
        return ConnectorSetupSession(
            session_id=row.id,
            connector_name=row.connector_name,
            erp_url=row.erp_url,
            erp_url_host=row.erp_url_host,
            environment_type=ConnectorSetupEnvironmentType(row.environment_type),
            submitted_by=row.submitted_by,
            status=ConnectorSetupStatus(row.status),
            credential_mode=ConnectorSetupCredentialMode(row.credential_mode),
            credential_ref=row.credential_ref,
            detected_adapter_type=row.detected_adapter_type,
            requires_credentials=requires_credentials,
            can_fingerprint=False,
            can_activate_read_only=False,
            will_connect=False,
            external_http_performed=False,
            credentials_stored=False,
            raw_credentials_seen=raw_credentials_seen,
            login_attempted=False,
            fingerprint_performed=False,
            schema_inspection_performed=False,
            capability_generation_performed=False,
            read_only_activation_performed=False,
            erp_write_performed=False,
            blocking_reasons=blocking_reasons,
            audit_recorded=True,
            created_at=str(row.created_at),
            updated_at=str(row.updated_at),
        )


def normalize_erp_url_host(erp_url: str) -> tuple[str, list[str]]:
    parsed = urlparse(erp_url.strip())
    if not parsed.scheme or not parsed.hostname:
        return "", ["invalid_erp_url"]

    scheme = parsed.scheme.lower()
    host = parsed.hostname.lower()
    if scheme == "https":
        return host, []

    if scheme == "http" and _is_localhost(host):
        return host, []

    if scheme == "http":
        return host, ["unsafe_url_scheme"]

    return host, ["unsafe_url_scheme"]


def _is_localhost(host: str) -> bool:
    return host in {"localhost", "127.0.0.1", "::1"} or host.endswith(".localhost")


def _normalize_optional_ref(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    return cleaned or None


def _from_json(value: str | None, fallback: Any):
    if not value:
        return fallback
    return json.loads(value)
