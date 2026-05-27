from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from erpguard.db.repositories import (
    create_manual_dry_run_audit_event,
    list_recent_manual_dry_run_audit_events,
)


@dataclass(frozen=True)
class ManualDryRunAuditEntry:
    event_id: str
    run_id: str
    version_id: str
    actor: dict[str, Any]
    event_type: str
    status: str
    detail: dict[str, Any]
    created_at: Any


@dataclass(frozen=True)
class ManualDryRunAuditResult:
    entries: list[ManualDryRunAuditEntry]
    event_count: int


def persist_manual_dry_run_audit_event(
    *,
    run_id: str,
    version_id: str,
    actor: dict[str, Any],
    event_type: str,
    status: str,
    detail: dict[str, Any],
    session,
) -> str:
    row = create_manual_dry_run_audit_event(
        session,
        run_id=run_id,
        version_id=version_id,
        actor_json=json.dumps(actor),
        event_type=event_type,
        status=status,
        detail_json=json.dumps(detail),
    )
    return row.id


def get_manual_dry_run_audit(*, session, limit: int = 50) -> ManualDryRunAuditResult:
    rows = list_recent_manual_dry_run_audit_events(session, limit=limit)
    entries = [
        ManualDryRunAuditEntry(
            event_id=row.id,
            run_id=row.run_id,
            version_id=row.version_id,
            actor=json.loads(row.actor_json or "{}"),
            event_type=row.event_type,
            status=row.status,
            detail=json.loads(row.detail_json or "{}"),
            created_at=row.created_at,
        )
        for row in rows
    ]
    return ManualDryRunAuditResult(entries=entries, event_count=len(entries))
