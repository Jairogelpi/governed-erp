from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from erpguard.db import repositories as repo
from erpguard.db.models import ExternalConnectorAuditEvent


@dataclass
class ExternalConnectorAuditEventModel:
    id: str
    auth_profile_id: str
    connector_id: str
    event_type: str
    operation: str
    status: str
    fixture_mode: bool
    actor: dict
    details: dict
    created_at: datetime

    def model_dump(self) -> dict:
        return {
            "id": self.id,
            "auth_profile_id": self.auth_profile_id,
            "connector_id": self.connector_id,
            "event_type": self.event_type,
            "operation": self.operation,
            "status": self.status,
            "fixture_mode": self.fixture_mode,
            "actor": self.actor,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }


_REDACT_KEYS = {"token", "access_token", "refresh_token", "secret", "password", "credential"}


def _redact_details(details: dict) -> dict:
    return {
        k: "[redacted]" if k.lower() in _REDACT_KEYS else v
        for k, v in details.items()
    }


class ExternalConnectorAuditService:
    def __init__(self, session: Session):
        self._session = session

    def record(
        self,
        *,
        auth_profile_id: str,
        connector_id: str,
        event_type: str,
        operation: str,
        status: str,
        fixture_mode: bool,
        actor: dict,
        details: dict,
    ) -> ExternalConnectorAuditEventModel:
        safe_details = _redact_details(details)
        row = repo.create_external_connector_audit_event(
            self._session,
            auth_profile_id=auth_profile_id,
            connector_id=connector_id,
            event_type=event_type,
            operation=operation,
            status=status,
            fixture_mode=fixture_mode,
            actor_json=json.dumps(actor),
            details_json=json.dumps(safe_details),
        )
        return self._to_model(row)

    def list_for_profile(self, auth_profile_id: str) -> list[ExternalConnectorAuditEventModel]:
        rows = repo.list_external_connector_audit_events_for_profile(self._session, auth_profile_id)
        return [self._to_model(r) for r in rows]

    def _to_model(self, row: ExternalConnectorAuditEvent) -> ExternalConnectorAuditEventModel:
        return ExternalConnectorAuditEventModel(
            id=row.id,
            auth_profile_id=row.auth_profile_id,
            connector_id=row.connector_id,
            event_type=row.event_type,
            operation=row.operation,
            status=row.status,
            fixture_mode=row.fixture_mode,
            actor=json.loads(row.actor_json),
            details=json.loads(row.details_json),
            created_at=row.created_at,
        )
