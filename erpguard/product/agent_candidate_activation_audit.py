from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from erpguard.db.repositories import (
    get_ui_skill_version_record,
    list_agent_candidate_activation_events_for_version,
    list_ui_skill_version_lifecycle_events,
)


@dataclass(frozen=True)
class ActivationAuditEntry:
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: datetime
    source: str  # "activation" or "lifecycle"


@dataclass(frozen=True)
class CandidateActivationAuditResult:
    version_id: str
    skill_id: str
    event_count: int
    lifecycle_event_count: int
    entries: list[ActivationAuditEntry] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True


def get_candidate_activation_audit(
    version_id: str, session
) -> CandidateActivationAuditResult:
    """Return the combined activation audit trail for a version."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return CandidateActivationAuditResult(
            version_id=version_id,
            skill_id="",
            event_count=0,
            lifecycle_event_count=0,
        )

    activation_rows = list_agent_candidate_activation_events_for_version(session, version_id)
    lifecycle_rows = list_ui_skill_version_lifecycle_events(session, version_id)

    entries: list[ActivationAuditEntry] = []
    for r in activation_rows:
        entries.append(ActivationAuditEntry(
            event_id=r.id,
            version_id=r.version_id,
            step=r.step,
            status=r.status,
            detail=json.loads(r.detail_json),
            created_at=r.created_at,
            source="activation",
        ))
    for lr in lifecycle_rows:
        entries.append(ActivationAuditEntry(
            event_id=lr.id,
            version_id=lr.version_id,
            step=lr.event_type,
            status=f"{lr.from_status}→{lr.to_status}",
            detail={"actor": lr.actor, "reason": lr.reason},
            created_at=lr.created_at,
            source="lifecycle",
        ))

    entries.sort(key=lambda e: e.created_at)

    return CandidateActivationAuditResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        event_count=len(entries),
        lifecycle_event_count=len(lifecycle_rows),
        entries=entries,
    )
