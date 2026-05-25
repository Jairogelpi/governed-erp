from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_ui_skill_version_record,
    list_agent_skill_run_preview_events_for_version,
)


@dataclass(frozen=True)
class PreviewAuditEvent:
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: object


@dataclass(frozen=True)
class RunPreviewAuditResult:
    version_id: str
    skill_id: str
    event_count: int
    events: list[PreviewAuditEvent] = field(default_factory=list)
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def get_run_preview_audit(version_id: str, session) -> RunPreviewAuditResult:
    """Return the ordered audit trail of run preview events."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return RunPreviewAuditResult(
            version_id=version_id,
            skill_id="",
            event_count=0,
        )

    rows = list_agent_skill_run_preview_events_for_version(session, version_id)
    events = [
        PreviewAuditEvent(
            event_id=r.id,
            version_id=r.version_id,
            step=r.step,
            status=r.status,
            detail=json.loads(r.detail_json),
            created_at=r.created_at,
        )
        for r in rows
    ]
    return RunPreviewAuditResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        event_count=len(events),
        events=events,
    )
