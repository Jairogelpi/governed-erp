from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Any

from erpguard.db.repositories import (
    create_action_dispatch_execution_audit_event,
    list_recent_action_dispatch_execution_audit_events,
)


@dataclass(frozen=True)
class DispatchExecutionAuditEntry:
    event_id: str
    dispatch_id: str
    action_key: str
    event_type: str
    status: str
    handler_type: str
    endpoint_hint: str
    method_hint: str
    token_id: str | None
    version_id: str | None
    detail: dict[str, Any] = field(default_factory=dict)
    created_at: Any = None


@dataclass(frozen=True)
class DispatchExecutionAuditResult:
    entries: list[DispatchExecutionAuditEntry]
    event_count: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def persist_dispatch_execution_event(
    *,
    dispatch_id: str,
    action_key: str,
    event_type: str,
    status: str,
    handler_type: str,
    endpoint_hint: str,
    method_hint: str,
    token_id: str | None,
    version_id: str | None,
    detail: dict[str, Any],
    session,
) -> str:
    event_id = f"adex_{uuid.uuid4().hex[:16]}"
    create_action_dispatch_execution_audit_event(
        session,
        event_id=event_id,
        dispatch_id=dispatch_id,
        action_key=action_key,
        event_type=event_type,
        status=status,
        handler_type=handler_type,
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        token_id=token_id,
        version_id=version_id,
        detail_json=json.dumps(detail, default=str, sort_keys=True),
    )
    return event_id


def get_dispatch_execution_audit(session, *, limit: int = 50) -> DispatchExecutionAuditResult:
    rows = list_recent_action_dispatch_execution_audit_events(session, limit=limit)
    return DispatchExecutionAuditResult(
        entries=[
            DispatchExecutionAuditEntry(
                event_id=row.id,
                dispatch_id=row.dispatch_id,
                action_key=row.action_key,
                event_type=row.event_type,
                status=row.status,
                handler_type=row.handler_type,
                endpoint_hint=row.endpoint_hint,
                method_hint=row.method_hint,
                token_id=row.token_id,
                version_id=row.version_id,
                detail=json.loads(row.detail_json or "{}"),
                created_at=row.created_at,
            )
            for row in rows
        ],
        event_count=len(rows),
    )
