from __future__ import annotations

from dataclasses import dataclass

from erpguard.db.repositories import (
    get_agent_candidate_activation_request_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
    list_agent_candidate_activation_events_for_version,
)


@dataclass(frozen=True)
class CandidateActivationStatusResult:
    version_id: str
    skill_id: str
    version_status: str
    is_active: bool
    latest_decision: str | None
    request_id: str
    request_status: str
    event_count: int
    is_executed: bool = False
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True


def get_candidate_activation_status(
    version_id: str, session
) -> CandidateActivationStatusResult:
    """Return the current activation status for a candidate version."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return CandidateActivationStatusResult(
            version_id=version_id,
            skill_id="",
            version_status="not_found",
            is_active=False,
            latest_decision=None,
            request_id="",
            request_status="not_found",
            event_count=0,
        )

    latest_decision = get_latest_agent_candidate_decision(session, version_id)
    req = get_agent_candidate_activation_request_by_version(session, version_id)
    events = list_agent_candidate_activation_events_for_version(session, version_id)

    return CandidateActivationStatusResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        version_status=version_row.status,
        is_active=version_row.is_active,
        latest_decision=latest_decision.decision if latest_decision else None,
        request_id=req.id if req else "",
        request_status=req.request_status if req else "not_requested",
        event_count=len(events),
    )
