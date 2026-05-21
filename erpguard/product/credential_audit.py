from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import create_connector_credential_audit_event, list_connector_credential_audit_events
from erpguard.product.credential_vault import CredentialVaultRecord


class CredentialAuditEventModel(BaseModel):
    event_id: str
    profile_id: str
    event_type: str
    status: str
    actor: dict[str, Any] = Field(default_factory=dict)
    details: dict[str, Any] = Field(default_factory=dict)
    secret_redacted: bool = True
    created_at: str | None = None


class CredentialAuditService:
    def __init__(self, session: Session):
        self.session = session

    def record(
        self,
        *,
        profile_id: str,
        event_type: str,
        status: str,
        actor: dict[str, Any] | None,
        vault_record: CredentialVaultRecord | None = None,
        details: dict[str, Any] | None = None,
    ) -> CredentialAuditEventModel:
        safe_details = dict(details or {})
        if vault_record is not None:
            safe_details.update(
                {
                    "credential_ref": vault_record.credential_ref,
                    "secret_fingerprint": vault_record.secret_fingerprint,
                    "secret_redacted": True,
                }
            )
        row = create_connector_credential_audit_event(
            self.session,
            profile_id=profile_id,
            event_type=event_type,
            status=status,
            actor_json=_to_json(actor or {}),
            details_json=_to_json(safe_details),
        )
        return self._model(row)

    def list(self, profile_id: str) -> list[CredentialAuditEventModel]:
        return [self._model(row) for row in list_connector_credential_audit_events(self.session, profile_id)]

    def _model(self, row) -> CredentialAuditEventModel:
        return CredentialAuditEventModel(
            event_id=row.id,
            profile_id=row.profile_id,
            event_type=row.event_type,
            status=row.status,
            actor=_from_json(row.actor_json, {}),
            details=_from_json(row.details_json, {}),
            secret_redacted=True,
            created_at=str(row.created_at),
        )


def _to_json(value: Any) -> str:
    import json

    return json.dumps(value, default=str)


def _from_json(value: str | None, fallback):
    import json

    if not value:
        return fallback
    return json.loads(value)
