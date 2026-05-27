from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from erpguard.db.repositories import (
    create_fake_erp_execution_audit_event,
    list_recent_fake_erp_execution_audit_events,
)


@dataclass(frozen=True)
class FakeERPExecutionAuditEntry:
    event_id: str
    execution_id: str
    version_id: str
    dry_run_id: str
    actor: dict[str, Any]
    event_type: str
    status: str
    detail: dict[str, Any]
    created_at: Any


@dataclass(frozen=True)
class FakeERPExecutionAuditResult:
    entries: list[FakeERPExecutionAuditEntry]
    event_count: int


def persist_fake_erp_execution_audit_event(
    *,
    execution_id: str,
    version_id: str,
    dry_run_id: str,
    actor: dict[str, Any],
    event_type: str,
    status: str,
    detail: dict[str, Any],
    session,
) -> str:
    row = create_fake_erp_execution_audit_event(
        session,
        execution_id=execution_id,
        version_id=version_id,
        dry_run_id=dry_run_id,
        actor_json=json.dumps(actor),
        event_type=event_type,
        status=status,
        detail_json=json.dumps(detail),
    )
    return row.id


def get_fake_erp_execution_audit(*, session, limit: int = 50) -> FakeERPExecutionAuditResult:
    rows = list_recent_fake_erp_execution_audit_events(session, limit=limit)
    entries = [
        FakeERPExecutionAuditEntry(
            event_id=row.id,
            execution_id=row.execution_id,
            version_id=row.version_id,
            dry_run_id=row.dry_run_id,
            actor=json.loads(row.actor_json or "{}"),
            event_type=row.event_type,
            status=row.status,
            detail=json.loads(row.detail_json or "{}"),
            created_at=row.created_at,
        )
        for row in rows
    ]
    return FakeERPExecutionAuditResult(entries=entries, event_count=len(entries))
