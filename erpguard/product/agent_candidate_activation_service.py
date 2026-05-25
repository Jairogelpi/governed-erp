from __future__ import annotations

import json
from dataclasses import dataclass

from erpguard.db.repositories import (
    create_agent_candidate_activation_event,
    create_ui_skill_version_lifecycle_event,
    get_active_ui_skill_version,
    get_ui_skill_version_record,
    update_ui_skill_version_status,
)
from erpguard.product.agent_candidate_activation_validator import (
    validate_candidate_for_activation,
)


@dataclass(frozen=True)
class CandidateActivationResult:
    version_id: str
    skill_id: str
    activated: bool
    prior_version_deactivated: bool
    prior_version_id: str
    version_status: str
    is_active: bool
    # Invariants
    is_executed: bool = False
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def activate_candidate_version(
    version_id: str,
    actor: str = "system",
    session=None,
) -> CandidateActivationResult:
    """Activate a governed candidate version. Does NOT execute it."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return CandidateActivationResult(
            version_id=version_id,
            skill_id="",
            activated=False,
            prior_version_deactivated=False,
            prior_version_id="",
            version_status="not_found",
            is_active=False,
            blocking_reason="version_not_found",
        )

    # Idempotent: already active
    if version_row.status == "active" and version_row.is_active:
        return CandidateActivationResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            activated=True,
            prior_version_deactivated=False,
            prior_version_id="",
            version_status="active",
            is_active=True,
        )

    validation = validate_candidate_for_activation(version_id, session)
    if not validation.eligible:
        return CandidateActivationResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            activated=False,
            prior_version_deactivated=False,
            prior_version_id="",
            version_status=version_row.status,
            is_active=False,
            blocking_reason="; ".join(validation.blocking_reasons),
        )

    # Deactivate the currently active version of the same skill, if any
    prior = get_active_ui_skill_version(session, version_row.skill_id)
    prior_version_id = ""
    prior_deactivated = False
    if prior is not None and prior.id != version_id:
        update_ui_skill_version_status(session, prior.id, status="superseded", is_active=False)
        create_ui_skill_version_lifecycle_event(
            session,
            version_id=prior.id,
            skill_id=prior.skill_id,
            event_type="deactivated",
            from_status="active",
            to_status="superseded",
            actor=actor,
            reason=f"Superseded by new activation of version {version_id}",
        )
        create_agent_candidate_activation_event(
            session,
            version_id=prior.id,
            skill_id=prior.skill_id,
            step="prior_version_deactivated",
            status="completed",
            detail_json=json.dumps({
                "prior_version_id": prior.id,
                "new_version_id": version_id,
            }),
        )
        prior_version_id = prior.id
        prior_deactivated = True

    # Activate this version
    update_ui_skill_version_status(session, version_id, status="active", is_active=True)

    create_ui_skill_version_lifecycle_event(
        session,
        version_id=version_id,
        skill_id=version_row.skill_id,
        event_type="activated",
        from_status="candidate",
        to_status="active",
        actor=actor,
        reason="Explicit activation after human approval and governance gate",
    )

    create_agent_candidate_activation_event(
        session,
        version_id=version_id,
        skill_id=version_row.skill_id,
        step="version_activated",
        status="completed",
        detail_json=json.dumps({
            "actor": actor,
            "prior_version_deactivated": prior_deactivated,
            "prior_version_id": prior_version_id,
            "is_executed": False,
            "can_execute": False,
        }),
    )

    return CandidateActivationResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        activated=True,
        prior_version_deactivated=prior_deactivated,
        prior_version_id=prior_version_id,
        version_status="active",
        is_active=True,
    )
