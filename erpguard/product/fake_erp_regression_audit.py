from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from erpguard.db.repositories import (
    create_fake_erp_regression_audit_event,
    list_recent_fake_erp_regression_audit_events,
)


@dataclass(frozen=True)
class FakeERPRegressionAuditEntry:
    event_id: str
    regression_run_id: str
    case_id: str
    version_id: str
    execution_id: str | None
    evidence_pack_id: str | None
    actor: dict
    event_type: str
    status: str
    detail: dict
    created_at: object


@dataclass(frozen=True)
class FakeERPRegressionAuditResult:
    entries: list[FakeERPRegressionAuditEntry]
    event_count: int


def persist_fake_erp_regression_audit_event(
    *,
    regression_run_id: str,
    case_id: str,
    version_id: str,
    execution_id: str | None,
    evidence_pack_id: str | None,
    actor: dict,
    event_type: str,
    status: str,
    detail: dict,
    session,
) -> FakeERPRegressionAuditEntry:
    row = create_fake_erp_regression_audit_event(
        session,
        audit_event_id=f"fera_{uuid4().hex[:16]}",
        regression_run_id=regression_run_id,
        case_id=case_id,
        version_id=version_id,
        execution_id=execution_id,
        evidence_pack_id=evidence_pack_id,
        actor_json=json.dumps(actor or {}),
        event_type=event_type,
        status=status,
        detail_json=json.dumps(detail or {}),
    )
    return FakeERPRegressionAuditEntry(
        event_id=row.id,
        regression_run_id=row.regression_run_id,
        case_id=row.case_id,
        version_id=row.version_id,
        execution_id=row.execution_id,
        evidence_pack_id=row.evidence_pack_id,
        actor=json.loads(row.actor_json or "{}"),
        event_type=row.event_type,
        status=row.status,
        detail=json.loads(row.detail_json or "{}"),
        created_at=row.created_at,
    )


def get_fake_erp_regression_audit(*, session, limit: int = 50) -> FakeERPRegressionAuditResult:
    rows = list_recent_fake_erp_regression_audit_events(session, limit=limit)
    entries = [
        FakeERPRegressionAuditEntry(
            event_id=row.id,
            regression_run_id=row.regression_run_id,
            case_id=row.case_id,
            version_id=row.version_id,
            execution_id=row.execution_id,
            evidence_pack_id=row.evidence_pack_id,
            actor=json.loads(row.actor_json or "{}"),
            event_type=row.event_type,
            status=row.status,
            detail=json.loads(row.detail_json or "{}"),
            created_at=row.created_at,
        )
        for row in rows
    ]
    return FakeERPRegressionAuditResult(entries=entries, event_count=len(entries))
