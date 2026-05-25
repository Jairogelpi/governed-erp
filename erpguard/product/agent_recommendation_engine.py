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
class Recommendation:
    priority: int
    action: str
    description: str
    endpoint_hint: str
    category: str = "governance"


@dataclass(frozen=True)
class RecommendationsResult:
    version_id: str
    skill_id: str
    recommendations: list[Recommendation] = field(default_factory=list)
    governance_complete: bool = False
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def get_recommendations(version_id: str, session) -> RecommendationsResult:
    """Generate ordered governance recommendations — reads only, never executes."""
    row = get_ui_skill_version_record(session, version_id)
    if row is None:
        return RecommendationsResult(
            version_id=version_id,
            skill_id="",
            blocking_reason="version_not_found",
        )

    recs: list[Recommendation] = []
    priority = 1

    decision = get_latest_agent_candidate_decision(session, version_id)
    if decision is None:
        recs.append(Recommendation(
            priority=priority,
            action="submit_human_decision",
            description="No human decision recorded. A reviewer must approve this candidate.",
            endpoint_hint=f"POST /v1/agent-builder/advisory/candidates/{version_id}/decision",
        ))
        priority += 1
    elif decision.decision != "approve":
        recs.append(Recommendation(
            priority=priority,
            action="resubmit_approval",
            description=f"Decision is '{decision.decision}'. Address feedback and resubmit as 'approve'.",
            endpoint_hint=f"POST /v1/agent-builder/advisory/candidates/{version_id}/decision",
        ))
        priority += 1

    req = get_agent_candidate_activation_request_by_version(session, version_id)
    if req is None:
        recs.append(Recommendation(
            priority=priority,
            action="create_activation_request",
            description="No activation request found. Create one after approval is on record.",
            endpoint_hint=f"POST /v1/agent-builder/advisory/candidates/{version_id}/activation-request",
        ))
        priority += 1

    req_events = list_agent_candidate_activation_request_events_for_version(session, version_id)
    gate_steps = {e.step for e in req_events}
    if "final_activation_gate_evaluated" not in gate_steps:
        recs.append(Recommendation(
            priority=priority,
            action="evaluate_final_gate",
            description="Evaluate the final activation gate to confirm all governance artifacts are in place.",
            endpoint_hint=f"GET /v1/agent-builder/advisory/candidates/{version_id}/activation-request/final-gate",
        ))
        priority += 1

    if row.status != "active" or not row.is_active:
        recs.append(Recommendation(
            priority=priority,
            action="activate_version",
            description="Activate the governed candidate to mark it as the live version.",
            endpoint_hint=f"POST /v1/agent-builder/advisory/candidates/{version_id}/activation/activate",
        ))
        priority += 1

    preview_events = list_agent_skill_run_preview_events_for_version(session, version_id)
    preview_steps = {e.step for e in preview_events}
    if "run_preview_completed" not in preview_steps:
        recs.append(Recommendation(
            priority=priority,
            action="run_preview",
            description="Execute a manual run preview to verify the skill plan and execution gate.",
            endpoint_hint=f"POST /v1/agent-builder/advisory/candidates/{version_id}/run-preview",
            category="preview",
        ))
        priority += 1

    if not recs:
        recs.append(Recommendation(
            priority=1,
            action="governance_complete",
            description="All governance steps are complete. This version is fully governed and previewed.",
            endpoint_hint=f"GET /v1/agent-builder/discovery/skills/{version_id}/lifecycle-summary",
            category="status",
        ))

    return RecommendationsResult(
        version_id=version_id,
        skill_id=row.skill_id,
        recommendations=recs,
        governance_complete=len(recs) == 1 and recs[0].action == "governance_complete",
    )
