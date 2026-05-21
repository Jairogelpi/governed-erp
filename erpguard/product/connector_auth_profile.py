from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_connector_auth_profile,
    get_connector_auth_profile,
    list_connector_auth_profiles,
    update_connector_auth_profile,
)
from erpguard.product.credential_audit import CredentialAuditEventModel, CredentialAuditService
from erpguard.product.credential_vault import CredentialVault
from erpguard.product.oauth_readiness import OAuthReadinessService


class ConnectorAuthProfileModel(BaseModel):
    profile_id: str
    connector_id: str
    display_name: str
    auth_type: str
    status: str
    requested_scopes: list[str] = Field(default_factory=list)
    credential_ref: str
    secret_fingerprint: str
    has_secret: bool = True
    secret_redacted: bool = True
    oauth_ready: bool = False
    oauth_flow_enabled: bool = False
    provider_api_calls_enabled: bool = False
    real_oauth_performed: bool = False
    created_by: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None


class ConnectorAuthProfileList(BaseModel):
    profiles: list[ConnectorAuthProfileModel] = Field(default_factory=list)


class ConnectorTestResult(BaseModel):
    profile_id: str
    connector_id: str
    test_status: str
    simulated: bool = True
    provider_api_called: bool = False
    real_oauth_performed: bool = False
    secret_redacted: bool = True
    message: str = "Connection test is simulated; no provider API was called."


class ConnectorAuthProfileService:
    def __init__(self, session: Session):
        self.session = session
        self.vault = CredentialVault()
        self.audit_service = CredentialAuditService(session)
        self.readiness_service = OAuthReadinessService()

    def create_profile(
        self,
        *,
        connector_id: str,
        display_name: str,
        auth_type: str,
        requested_scopes: list[str],
        credential: dict[str, Any] | None,
        created_by: dict[str, Any] | None = None,
    ) -> ConnectorAuthProfileModel:
        vault_record = self.vault.store(credential)
        readiness = self.readiness_service.readiness_for(connector_id, auth_type)
        row = create_connector_auth_profile(
            self.session,
            connector_id=connector_id,
            display_name=display_name,
            auth_type=auth_type,
            requested_scopes_json=_to_json(requested_scopes),
            credential_ref=vault_record.credential_ref,
            secret_fingerprint=vault_record.secret_fingerprint,
            created_by_actor_json=_to_json(created_by or {}),
            oauth_readiness_json=readiness.model_dump_json(),
            status="active",
        )
        self.audit_service.record(
            profile_id=row.id,
            event_type="profile_created",
            status="completed",
            actor=created_by,
            vault_record=vault_record,
            details={"connector_id": connector_id, "auth_type": auth_type, "requested_scopes": requested_scopes},
        )
        return self._model(row)

    def list_profiles(self) -> list[ConnectorAuthProfileModel]:
        return [self._model(row) for row in list_connector_auth_profiles(self.session)]

    def get_profile(self, profile_id: str) -> ConnectorAuthProfileModel:
        row = get_connector_auth_profile(self.session, profile_id)
        if row is None:
            raise ObjectNotFoundError(f"Connector auth profile '{profile_id}' was not found.")
        return self._model(row)

    def simulate_test(self, profile_id: str, actor: dict[str, Any] | None = None) -> ConnectorTestResult:
        profile = self.get_profile(profile_id)
        status = "simulated_blocked" if profile.status == "revoked" else "simulated_passed"
        self.audit_service.record(
            profile_id=profile_id,
            event_type="simulated_connection_test",
            status=status,
            actor=actor,
            details={
                "connector_id": profile.connector_id,
                "provider_api_called": False,
                "real_oauth_performed": False,
                "secret_redacted": True,
            },
        )
        return ConnectorTestResult(profile_id=profile_id, connector_id=profile.connector_id, test_status=status)

    def rotate(
        self,
        profile_id: str,
        credential: dict[str, Any] | None,
        actor: dict[str, Any] | None = None,
    ) -> ConnectorAuthProfileModel:
        self.get_profile(profile_id)
        vault_record = self.vault.store(credential)
        row = update_connector_auth_profile(
            self.session,
            profile_id,
            credential_ref=vault_record.credential_ref,
            secret_fingerprint=vault_record.secret_fingerprint,
            status="rotated",
        )
        if row is None:
            raise ObjectNotFoundError(f"Connector auth profile '{profile_id}' was not found.")
        self.audit_service.record(
            profile_id=profile_id,
            event_type="credential_rotated",
            status="completed",
            actor=actor,
            vault_record=vault_record,
        )
        return self._model(row)

    def revoke(self, profile_id: str, actor: dict[str, Any] | None = None) -> ConnectorAuthProfileModel:
        self.get_profile(profile_id)
        row = update_connector_auth_profile(self.session, profile_id, status="revoked")
        if row is None:
            raise ObjectNotFoundError(f"Connector auth profile '{profile_id}' was not found.")
        self.audit_service.record(
            profile_id=profile_id,
            event_type="credential_revoked",
            status="completed",
            actor=actor,
            details={"secret_redacted": True},
        )
        return self._model(row)

    def audit(self, profile_id: str) -> list[CredentialAuditEventModel]:
        self.get_profile(profile_id)
        return self.audit_service.list(profile_id)

    def _model(self, row) -> ConnectorAuthProfileModel:
        readiness = _from_json(row.oauth_readiness_json, {})
        return ConnectorAuthProfileModel(
            profile_id=row.id,
            connector_id=row.connector_id,
            display_name=row.display_name,
            auth_type=row.auth_type,
            status=row.status,
            requested_scopes=_from_json(row.requested_scopes_json, []),
            credential_ref=row.credential_ref,
            secret_fingerprint=row.secret_fingerprint,
            has_secret=bool(row.credential_ref),
            secret_redacted=True,
            oauth_ready=bool(readiness.get("oauth_ready", False)),
            oauth_flow_enabled=bool(readiness.get("oauth_flow_enabled", False)),
            provider_api_calls_enabled=bool(readiness.get("provider_api_calls_enabled", False)),
            real_oauth_performed=False,
            created_by=_from_json(row.created_by_actor_json, {}),
            created_at=str(row.created_at),
            updated_at=str(row.updated_at),
        )


def _to_json(value: Any) -> str:
    import json

    return json.dumps(value, default=str)


def _from_json(value: str | None, fallback):
    import json

    if not value:
        return fallback
    return json.loads(value)
