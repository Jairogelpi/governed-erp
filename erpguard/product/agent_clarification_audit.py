from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import list_clarification_audit_events_for_proposal


class AuditEntry(BaseModel):
    event_id: str
    event_type: str
    detail: dict = Field(default_factory=dict)
    created_at: str


class ClarificationAudit(BaseModel):
    proposal_id: str
    event_count: int
    events: list[AuditEntry] = Field(default_factory=list)
    is_advisory_only: bool = True
    can_execute: bool = False


def get_clarification_audit(proposal_id: str, session: Session) -> ClarificationAudit:
    rows = list_clarification_audit_events_for_proposal(session, proposal_id)
    entries = [
        AuditEntry(
            event_id=row.id,
            event_type=row.event_type,
            detail=json.loads(row.detail_json or "{}"),
            created_at=row.created_at.isoformat(),
        )
        for row in rows
    ]
    return ClarificationAudit(
        proposal_id=proposal_id,
        event_count=len(entries),
        events=entries,
        is_advisory_only=True,
        can_execute=False,
    )
