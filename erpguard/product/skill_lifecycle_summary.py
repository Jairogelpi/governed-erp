from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from erpguard.db.repositories import (
    get_agent_candidate_activation_request_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
    list_agent_skill_run_preview_events_for_version,
    list_ui_skill_version_lifecycle_events,
)


@dataclass(frozen=True)
class LifecycleEvent:
    event_type: str
    from_status: str
    to_status: str
    actor: str
    created_at: datetime


@dataclass(frozen=True)
class SkillLifecycleSummary:
    version_id: str
    skill_id: str
    name: str
    status: str
    is_active: bool
    runtime_type: str
    governance_status: str
    has_human_decision: bool
    human_decision: str
    has_activation_request: bool
    has_run_preview: bool
    llm_required: bool
    lifecycle_events: list[LifecycleEvent] = field(default_factory=list)
    preview_event_count: int = 0
    blocking_reason: str = ""
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def get_lifecycle_summary(version_id: str, session) -> SkillLifecycleSummary:
    """Return a full lifecycle summary for a skill version — reads only, never executes."""
    row = get_ui_skill_version_record(session, version_id)
    if row is None:
        return SkillLifecycleSummary(
            version_id=version_id,
            skill_id="",
            name="",
            status="unknown",
            is_active=False,
            runtime_type="",
            governance_status="unknown",
            has_human_decision=False,
            human_decision="",
            has_activation_request=False,
            has_run_preview=False,
            llm_required=False,
            blocking_reason="version_not_found",
        )

    decision = get_latest_agent_candidate_decision(session, version_id)
    activation_req = get_agent_candidate_activation_request_by_version(session, version_id)
    lifecycle_rows = list_ui_skill_version_lifecycle_events(session, version_id)
    preview_events = list_agent_skill_run_preview_events_for_version(session, version_id)

    has_run_preview = any(e.step == "run_preview_completed" for e in preview_events)

    lifecycle_events = [
        LifecycleEvent(
            event_type=e.event_type,
            from_status=e.from_status,
            to_status=e.to_status,
            actor=e.actor,
            created_at=e.created_at,
        )
        for e in lifecycle_rows
    ]

    if row.status == "active" and row.is_active:
        governance_status = "active_governed"
    elif row.status == "superseded":
        governance_status = "superseded"
    elif row.status == "candidate":
        if decision and decision.decision == "approve":
            governance_status = "approved_pending_activation"
        elif decision:
            governance_status = f"decision_{decision.decision}"
        else:
            governance_status = "pending_review"
    else:
        governance_status = row.status

    return SkillLifecycleSummary(
        version_id=version_id,
        skill_id=row.skill_id,
        name=row.name,
        status=row.status,
        is_active=row.is_active,
        runtime_type=row.runtime_type,
        governance_status=governance_status,
        has_human_decision=decision is not None,
        human_decision=decision.decision if decision else "",
        has_activation_request=activation_req is not None,
        has_run_preview=has_run_preview,
        llm_required=row.llm_required,
        lifecycle_events=lifecycle_events,
        preview_event_count=len(preview_events),
    )
