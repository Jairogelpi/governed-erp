from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_automation_draft,
    list_agent_draft_handoff_events_for_draft,
)


class HandoffAuditEntry(BaseModel):
    event_id: str
    step: str
    status: str
    detail: dict
    created_at: str


class DraftHandoffAudit(BaseModel):
    draft_id: str
    event_count: int
    events: list[HandoffAuditEntry] = Field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True


def get_handoff_audit(draft_id: str, session: Session) -> DraftHandoffAudit:
    _ = get_automation_draft(session, draft_id)

    raw_events = list_agent_draft_handoff_events_for_draft(session, draft_id)
    entries: list[HandoffAuditEntry] = []
    for ev in raw_events:
        try:
            detail = json.loads(ev.detail_json)
        except (json.JSONDecodeError, ValueError):
            detail = {}
        entries.append(HandoffAuditEntry(
            event_id=ev.id,
            step=ev.step,
            status=ev.status,
            detail=detail,
            created_at=ev.created_at.isoformat(),
        ))

    return DraftHandoffAudit(
        draft_id=draft_id,
        event_count=len(entries),
        events=entries,
        can_execute=False,
        is_advisory_only=True,
    )
