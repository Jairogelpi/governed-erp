from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_agent_candidate_activation_request_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
    list_agent_candidate_activation_events_for_version,
    list_ui_skill_version_lifecycle_events,
)


@dataclass(frozen=True)
class PostActivationSummary:
    version_id: str
    skill_id: str
    version_status: str
    runtime_type: str
    is_active: bool
    latest_decision: str | None
    governance_status: str
    request_id: str
    request_status: str
    activation_event_count: int
    lifecycle_event_count: int
    summary_notes: list[str] = field(default_factory=list)
    is_executed: bool = False
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True


_GOVERNANCE_LABELS = {
    "approve": "approved_pending_activation",
    "reject": "rejected",
    "request_changes": "changes_requested",
}


def get_post_activation_summary(
    version_id: str, session
) -> PostActivationSummary:
    """Return a full post-activation governance summary for a version."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return PostActivationSummary(
            version_id=version_id,
            skill_id="",
            version_status="not_found",
            runtime_type="",
            is_active=False,
            latest_decision=None,
            governance_status="blocked",
            request_id="",
            request_status="not_found",
            activation_event_count=0,
            lifecycle_event_count=0,
            summary_notes=["Version not found"],
        )

    latest_decision = get_latest_agent_candidate_decision(session, version_id)
    req = get_agent_candidate_activation_request_by_version(session, version_id)
    activation_events = list_agent_candidate_activation_events_for_version(session, version_id)
    lifecycle_events = list_ui_skill_version_lifecycle_events(session, version_id)

    decision_str = latest_decision.decision if latest_decision else None
    if version_row.status == "active":
        governance_status = "active_governed"
    elif decision_str:
        governance_status = _GOVERNANCE_LABELS.get(decision_str, "unknown")
    else:
        governance_status = "pending"

    notes: list[str] = [
        "Activation does not imply execution — no run has been created.",
        "Execution requires a separate, explicitly authorized step.",
        f"Version governance status: {governance_status}.",
    ]
    if version_row.is_active:
        notes.append("Version is the current active governed version for this skill.")
    if req:
        notes.append(f"Activation request {req.id} is on record (status: {req.request_status}).")

    return PostActivationSummary(
        version_id=version_id,
        skill_id=version_row.skill_id,
        version_status=version_row.status,
        runtime_type=version_row.runtime_type,
        is_active=version_row.is_active,
        latest_decision=decision_str,
        governance_status=governance_status,
        request_id=req.id if req else "",
        request_status=req.request_status if req else "not_requested",
        activation_event_count=len(activation_events),
        lifecycle_event_count=len(lifecycle_events),
        summary_notes=notes,
    )
