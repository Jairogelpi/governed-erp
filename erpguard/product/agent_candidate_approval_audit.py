from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_candidate_approval_packet_by_version,
    get_ui_skill_version_record,
    list_agent_candidate_approval_events_for_version,
)


@dataclass(frozen=True)
class ApprovalAuditEntry:
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: str


@dataclass(frozen=True)
class AgentCandidateApprovalAuditResult:
    version_id: str
    skill_id: str
    approval_packet_id: str | None
    event_count: int
    events: list[ApprovalAuditEntry] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True


def get_approval_audit(version_id: str, session) -> AgentCandidateApprovalAuditResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateApprovalAuditResult(
            version_id=version_id,
            skill_id="",
            approval_packet_id=None,
            event_count=0,
        )

    rows = list_agent_candidate_approval_events_for_version(session, version_id)
    pkt = get_agent_candidate_approval_packet_by_version(session, version_id)

    entries = [
        ApprovalAuditEntry(
            event_id=r.id,
            version_id=r.version_id,
            step=r.step,
            status=r.status,
            detail=json.loads(r.detail_json) if r.detail_json else {},
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]

    return AgentCandidateApprovalAuditResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        approval_packet_id=pkt.id if pkt else None,
        event_count=len(entries),
        events=entries,
    )
