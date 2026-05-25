from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.product.agent_recommendation_engine import get_recommendations
from erpguard.product.governance_gap_explainer import explain_governance_gaps


@dataclass(frozen=True)
class NextStep:
    step_number: int
    action: str
    rationale: str
    endpoint_hint: str
    severity: str  # "blocking", "warning", "info", "complete"


@dataclass(frozen=True)
class NextStepRecommendation:
    version_id: str
    skill_id: str
    governance_status: str
    next_steps: list[NextStep] = field(default_factory=list)
    step_count: int = 0
    all_steps_complete: bool = False
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def recommend_next_steps(version_id: str, session) -> NextStepRecommendation:
    """Produce ordered operator guidance from current governance state — reads only, never executes."""
    row = get_ui_skill_version_record(session, version_id)
    if row is None:
        return NextStepRecommendation(
            version_id=version_id,
            skill_id="",
            governance_status="unknown",
            blocking_reason="version_not_found",
        )

    gaps_result = explain_governance_gaps(version_id, session)
    recs_result = get_recommendations(version_id, session)

    # Map severity
    severity_map = {"blocking": "blocking", "warning": "warning", "info": "info"}
    steps: list[NextStep] = []
    step_num = 1

    # Prioritise blocking gaps first
    for gap in gaps_result.gaps:
        steps.append(NextStep(
            step_number=step_num,
            action=gap.gap_type,
            rationale=gap.description,
            endpoint_hint=gap.suggested_action,
            severity=severity_map.get(gap.severity, "info"),
        ))
        step_num += 1

    # Layer in any recommendations not already covered by gaps
    covered = {g.gap_type for g in gaps_result.gaps}
    for rec in recs_result.recommendations:
        if rec.action not in covered and rec.action != "governance_complete":
            steps.append(NextStep(
                step_number=step_num,
                action=rec.action,
                rationale=rec.description,
                endpoint_hint=rec.endpoint_hint,
                severity="info",
            ))
            step_num += 1

    if not steps:
        steps.append(NextStep(
            step_number=1,
            action="governance_complete",
            rationale="All governance steps are complete. This version is fully governed.",
            endpoint_hint=f"GET /v1/agent-builder/discovery/skills/{version_id}/lifecycle-summary",
            severity="complete",
        ))

    governance_status = "active_governed" if row.status == "active" and row.is_active else row.status
    all_complete = len(steps) == 1 and steps[0].action == "governance_complete"

    return NextStepRecommendation(
        version_id=version_id,
        skill_id=row.skill_id,
        governance_status=governance_status,
        next_steps=steps,
        step_count=len(steps),
        all_steps_complete=all_complete,
    )
