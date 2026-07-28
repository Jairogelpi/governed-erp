from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime

from erpguard.db.repositories import (
    get_ui_skill_version_record,
    list_agent_candidate_activation_request_events_for_version,
)


@dataclass(frozen=True)
class RequestAuditEvent:
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: datetime


@dataclass(frozen=True)
class ActivationRequestAuditResult:
    version_id: str
    skill_id: str
    event_count: int
    events: list[RequestAuditEvent] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True


def get_activation_request_audit(
    version_id: str, session
) -> ActivationRequestAuditResult:
    """Return the ordered audit trail of activation request events."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return ActivationRequestAuditResult(
            version_id=version_id,
            skill_id="",
            event_count=0,
        )

    rows = list_agent_candidate_activation_request_events_for_version(session, version_id)
    events = [
        RequestAuditEvent(
            event_id=r.id,
            version_id=r.version_id,
            step=r.step,
            status=r.status,
            detail=json.loads(r.detail_json),
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ActivationRequestAuditResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        event_count=len(events),
        events=events,
    )
