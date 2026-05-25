from __future__ import annotations

import json
from dataclasses import dataclass

from erpguard.db.repositories import (
    create_agent_candidate_activation_request,
    create_agent_candidate_activation_request_event,
    get_agent_candidate_activation_request_by_version,
    get_ui_skill_version_record,
)
from erpguard.product.agent_candidate_activation_request_validator import (
    validate_activation_request_eligibility,
)


@dataclass(frozen=True)
class ActivationRequestResult:
    version_id: str
    skill_id: str
    request_id: str
    request_status: str
    requested_by: str
    rationale: str
    eligible: bool
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def create_activation_request(
    version_id: str,
    requested_by: str,
    rationale: str = "",
    session=None,
) -> ActivationRequestResult:
    """Create an explicit activation request artifact — does not activate the skill."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return ActivationRequestResult(
            version_id=version_id,
            skill_id="",
            request_id="",
            request_status="blocked",
            requested_by=requested_by,
            rationale=rationale,
            eligible=False,
            blocking_reason="version_not_found",
        )

    validation = validate_activation_request_eligibility(version_id, session)
    if not validation.eligible:
        return ActivationRequestResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            request_id="",
            request_status="blocked",
            requested_by=requested_by,
            rationale=rationale,
            eligible=False,
            blocking_reason="; ".join(validation.blocking_reasons),
        )

    # Idempotent: return existing request if already created
    existing = get_agent_candidate_activation_request_by_version(session, version_id)
    if existing is not None:
        return ActivationRequestResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            request_id=existing.id,
            request_status=existing.request_status,
            requested_by=existing.requested_by,
            rationale=existing.rationale,
            eligible=True,
        )

    req = create_agent_candidate_activation_request(
        session,
        version_id=version_id,
        skill_id=version_row.skill_id,
        requested_by=requested_by,
        rationale=rationale,
        detail_json=json.dumps({
            "version_status": version_row.status,
            "runtime_type": version_row.runtime_type,
            "can_execute": False,
            "is_advisory_only": True,
        }),
    )

    create_agent_candidate_activation_request_event(
        session, version_id, "activation_request_created", "completed",
        json.dumps({
            "request_id": req.id,
            "requested_by": requested_by,
            "request_status": req.request_status,
        }),
    )

    return ActivationRequestResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        request_id=req.id,
        request_status=req.request_status,
        requested_by=req.requested_by,
        rationale=req.rationale,
        eligible=True,
    )
