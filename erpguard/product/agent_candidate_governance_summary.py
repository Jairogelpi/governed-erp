from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_candidate_approval_packet_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
    list_agent_candidate_decisions_for_version,
)

_GOVERNANCE_STATUS_LABELS = {
    "approved_pending_activation": "Approved — awaiting explicit human activation",
    "rejected": "Rejected — version will not be promoted",
    "changes_requested": "Changes requested — requires revision before re-review",
    "pending": "Pending — no decision recorded yet",
}


@dataclass(frozen=True)
class AgentCandidateGovernanceSummaryResult:
    version_id: str
    skill_id: str
    version_status: str
    runtime_type: str
    approval_packet_exists: bool
    decision_count: int
    latest_decision: str | None
    governance_status: str
    governance_label: str
    is_ready_for_activation_gate: bool
    summary_notes: list[str] = field(default_factory=list)
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True


def get_governance_summary(
    version_id: str, session
) -> AgentCandidateGovernanceSummaryResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return AgentCandidateGovernanceSummaryResult(
            version_id=version_id,
            skill_id="",
            version_status="not_found",
            runtime_type="unknown",
            approval_packet_exists=False,
            decision_count=0,
            latest_decision=None,
            governance_status="blocked",
            governance_label="Version not found",
            is_ready_for_activation_gate=False,
        )

    approval_pkt = get_agent_candidate_approval_packet_by_version(session, version_id)
    decisions = list_agent_candidate_decisions_for_version(session, version_id)
    latest = get_latest_agent_candidate_decision(session, version_id)

    governance_status = "pending"
    if latest is not None:
        governance_status = {
            "approve": "approved_pending_activation",
            "reject": "rejected",
            "request_changes": "changes_requested",
        }.get(latest.decision, "unknown")

    governance_label = _GOVERNANCE_STATUS_LABELS.get(
        governance_status, governance_status
    )

    is_ready = (
        version_row.status == "candidate"
        and approval_pkt is not None
        and latest is not None
        and latest.decision == "approve"
    )

    notes: list[str] = []
    notes.append(f"Version lifecycle status: '{version_row.status}'")
    notes.append(f"Runtime type: '{version_row.runtime_type}'")
    notes.append(
        f"Approval packet: {'present' if approval_pkt else 'not created — run approval-request first'}"
    )
    notes.append(
        f"Decisions recorded: {len(decisions)}"
        + (f" (latest: {latest.decision} by {latest.actor})" if latest else "")
    )
    notes.append("Activation gate: evaluates only — does not activate automatically")
    notes.append("Human activation action required after gate passes")

    return AgentCandidateGovernanceSummaryResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        version_status=version_row.status,
        runtime_type=version_row.runtime_type,
        approval_packet_exists=approval_pkt is not None,
        decision_count=len(decisions),
        latest_decision=latest.decision if latest else None,
        governance_status=governance_status,
        governance_label=governance_label,
        is_ready_for_activation_gate=is_ready,
        summary_notes=notes,
    )
