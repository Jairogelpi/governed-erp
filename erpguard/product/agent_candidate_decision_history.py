from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_ui_skill_version_record,
    list_agent_candidate_decisions_for_version,
)

_GOVERNANCE_STATUS = {
    "approve": "approved_pending_activation",
    "reject": "rejected",
    "request_changes": "changes_requested",
}


@dataclass(frozen=True)
class DecisionEntry:
    decision_id: str
    version_id: str
    decision: str
    actor: str
    rationale: str
    governance_status: str
    created_at: str


@dataclass(frozen=True)
class AgentCandidateDecisionHistoryResult:
    version_id: str
    skill_id: str
    decision_count: int
    latest_decision: str | None
    latest_governance_status: str | None
    entries: list[DecisionEntry] = field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True


def get_decision_history(
    version_id: str, session
) -> AgentCandidateDecisionHistoryResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateDecisionHistoryResult(
            version_id=version_id,
            skill_id="",
            decision_count=0,
            latest_decision=None,
            latest_governance_status=None,
        )

    rows = list_agent_candidate_decisions_for_version(session, version_id)
    entries = [
        DecisionEntry(
            decision_id=r.id,
            version_id=r.version_id,
            decision=r.decision,
            actor=r.actor,
            rationale=r.rationale,
            governance_status=_GOVERNANCE_STATUS.get(r.decision, "unknown"),
            created_at=r.created_at.isoformat(),
        )
        for r in rows
    ]

    latest = entries[-1] if entries else None

    return AgentCandidateDecisionHistoryResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        decision_count=len(entries),
        latest_decision=latest.decision if latest else None,
        latest_governance_status=latest.governance_status if latest else None,
        entries=entries,
    )
