from __future__ import annotations

from dataclasses import dataclass

from erpguard.db.repositories import (
    get_agent_candidate_activation_request_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
    list_agent_candidate_activation_request_events_for_version,
)


@dataclass(frozen=True)
class ActivationRequestStatusResult:
    version_id: str
    skill_id: str
    request_id: str
    request_status: str
    requested_by: str
    rationale: str
    event_count: int
    latest_decision: str | None
    version_status: str
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True


def get_activation_request_status(
    version_id: str, session
) -> ActivationRequestStatusResult:
    """Return current status of the activation request for a version."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return ActivationRequestStatusResult(
            version_id=version_id,
            skill_id="",
            request_id="",
            request_status="not_found",
            requested_by="",
            rationale="",
            event_count=0,
            latest_decision=None,
            version_status="not_found",
        )

    req = get_agent_candidate_activation_request_by_version(session, version_id)
    events = list_agent_candidate_activation_request_events_for_version(session, version_id)
    latest_decision = get_latest_agent_candidate_decision(session, version_id)

    return ActivationRequestStatusResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        request_id=req.id if req else "",
        request_status=req.request_status if req else "not_requested",
        requested_by=req.requested_by if req else "",
        rationale=req.rationale if req else "",
        event_count=len(events),
        latest_decision=latest_decision.decision if latest_decision else None,
        version_status=version_row.status,
    )
