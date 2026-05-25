from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_ui_skill_version_record,
    list_agent_candidate_decision_events_for_version,
    list_agent_candidate_decisions_for_version,
)


@dataclass(frozen=True)
class DecisionAuditEntry:
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: str


@dataclass(frozen=True)
class AgentCandidateDecisionAuditResult:
    version_id: str
    skill_id: str
    decision_count: int
    event_count: int
    events: list[DecisionAuditEntry] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True


def get_decision_audit(version_id: str, session) -> AgentCandidateDecisionAuditResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateDecisionAuditResult(
            version_id=version_id,
            skill_id="",
            decision_count=0,
            event_count=0,
        )

    decisions = list_agent_candidate_decisions_for_version(session, version_id)
    rows = list_agent_candidate_decision_events_for_version(session, version_id)

    entries = [
        DecisionAuditEntry(
            event_id=r.id,
            version_id=r.version_id,
            step=r.step,
            status=r.status,
            detail=json.loads(r.detail_json) if r.detail_json else {},
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]

    return AgentCandidateDecisionAuditResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        decision_count=len(decisions),
        event_count=len(entries),
        events=entries,
    )
