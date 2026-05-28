from __future__ import annotations

import json
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_connector_setup_audit_event,
    list_connector_setup_audit_events,
)


class ConnectorSetupAuditEvent(BaseModel):
    event_id: str
    session_id: str
    event_type: str
    status: str
    submitted_by: str
    detail: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ConnectorSetupAuditLog(BaseModel):
    events: list[ConnectorSetupAuditEvent] = Field(default_factory=list)
    event_count: int = 0


class ConnectorSetupAuditService:
    def __init__(self, session: Session):
        self.session = session

    def record(
        self,
        *,
        session_id: str,
        event_type: str,
        status: str,
        submitted_by: str,
        detail: dict[str, Any] | None = None,
    ) -> ConnectorSetupAuditEvent:
        safe_detail = _redact_detail(detail or {})
        row = create_connector_setup_audit_event(
            self.session,
            event_id=f"csaud_{uuid4().hex[:16]}",
            session_id=session_id,
            event_type=event_type,
            status=status,
            submitted_by=submitted_by,
            detail_json=json.dumps(safe_detail, default=str),
        )
        return self._model(row)

    def list_events(self) -> ConnectorSetupAuditLog:
        events = [self._model(row) for row in list_connector_setup_audit_events(self.session)]
        return ConnectorSetupAuditLog(events=events, event_count=len(events))

    def _model(self, row) -> ConnectorSetupAuditEvent:
        return ConnectorSetupAuditEvent(
            event_id=row.id,
            session_id=row.session_id,
            event_type=row.event_type,
            status=row.status,
            submitted_by=row.submitted_by,
            detail=_from_json(row.detail_json, {}),
            created_at=str(row.created_at),
        )


SENSITIVE_DETAIL_KEYS = {
    "password",
    "api_key",
    "token",
    "secret",
    "credential",
    "credentials",
}


def _redact_detail(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in SENSITIVE_DETAIL_KEYS:
                redacted[str(key)] = "[redacted]"
            else:
                redacted[str(key)] = _redact_detail(item)
        return redacted
    if isinstance(value, list):
        return [_redact_detail(item) for item in value]
    return value


def _from_json(value: str | None, fallback):
    if not value:
        return fallback
    return json.loads(value)
