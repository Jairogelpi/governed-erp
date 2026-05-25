from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_candidate_activation_request_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
    list_agent_candidate_activation_request_events_for_version,
    list_agent_skill_run_preview_events_for_version,
)


@dataclass(frozen=True)
class GovernanceGap:
    gap_type: str
    description: str
    severity: str  # "blocking", "warning", "info"
    suggested_action: str


@dataclass(frozen=True)
class GovernanceGapsResult:
    version_id: str
    skill_id: str
    gaps: list[GovernanceGap] = field(default_factory=list)
    gap_count: int = 0
    is_fully_governed: bool = False
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def explain_governance_gaps(version_id: str, session) -> GovernanceGapsResult:
    """Identify governance gaps for a skill version — reads only, never executes."""
    row = get_ui_skill_version_record(session, version_id)
    if row is None:
        return GovernanceGapsResult(
            version_id=version_id,
            skill_id="",
            blocking_reason="version_not_found",
        )

    gaps: list[GovernanceGap] = []

    # Gap 1 — version still in draft/candidate
    if row.status not in ("active", "candidate"):
        gaps.append(GovernanceGap(
            gap_type="version_not_candidate",
            description=f"Version is in status '{row.status}'. Must reach 'candidate' before governance review.",
            severity="blocking",
            suggested_action="Promote the version to candidate status through the agent builder pipeline.",
        ))

    # Gap 2 — no human decision
    decision = get_latest_agent_candidate_decision(session, version_id)
    if decision is None:
        gaps.append(GovernanceGap(
            gap_type="no_human_decision",
            description="No human decision (approve/reject/request_changes) has been recorded.",
            severity="blocking",
            suggested_action="POST /v1/agent-builder/advisory/candidates/{version_id}/decision",
        ))
    elif decision.decision != "approve":
        gaps.append(GovernanceGap(
            gap_type="decision_not_approved",
            description=f"Latest human decision is '{decision.decision}', not 'approve'.",
            severity="blocking",
            suggested_action="Submit a new 'approve' decision after addressing feedback.",
        ))

    # Gap 3 — no activation request
    req = get_agent_candidate_activation_request_by_version(session, version_id)
    if req is None:
        gaps.append(GovernanceGap(
            gap_type="no_activation_request",
            description="No explicit activation request has been submitted.",
            severity="blocking",
            suggested_action="POST /v1/agent-builder/advisory/candidates/{version_id}/activation-request",
        ))

    # Gap 4 — final gate not evaluated
    req_events = list_agent_candidate_activation_request_events_for_version(session, version_id)
    gate_steps = {e.step for e in req_events}
    if "final_activation_gate_evaluated" not in gate_steps:
        gaps.append(GovernanceGap(
            gap_type="final_gate_not_evaluated",
            description="The final activation gate has not been evaluated.",
            severity="blocking",
            suggested_action="GET /v1/agent-builder/advisory/candidates/{version_id}/activation-request/final-gate",
        ))

    # Gap 5 — not active
    if row.status != "active" or not row.is_active:
        gaps.append(GovernanceGap(
            gap_type="not_activated",
            description="Version has not been activated. Activation marks it as a governed active version.",
            severity="warning",
            suggested_action="POST /v1/agent-builder/advisory/candidates/{version_id}/activation/activate",
        ))

    # Gap 6 — run preview never executed
    preview_events = list_agent_skill_run_preview_events_for_version(session, version_id)
    preview_steps = {e.step for e in preview_events}
    if "run_preview_completed" not in preview_steps:
        gaps.append(GovernanceGap(
            gap_type="preview_not_run",
            description="No manual run preview has been completed for this version.",
            severity="info",
            suggested_action="POST /v1/agent-builder/advisory/candidates/{version_id}/run-preview",
        ))

    is_fully_governed = len(gaps) == 0
    return GovernanceGapsResult(
        version_id=version_id,
        skill_id=row.skill_id,
        gaps=gaps,
        gap_count=len(gaps),
        is_fully_governed=is_fully_governed,
    )
