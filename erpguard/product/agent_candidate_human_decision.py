from __future__ import annotations

import json
from dataclasses import dataclass

from erpguard.db.repositories import (
    create_agent_candidate_decision,
    create_agent_candidate_decision_event,
    get_ui_skill_version_record,
)
from erpguard.product.agent_candidate_decision_validator import validate_human_decision

_GOVERNANCE_STATUS = {
    "approve": "approved_pending_activation",
    "reject": "rejected",
    "request_changes": "changes_requested",
}


@dataclass(frozen=True)
class HumanDecisionResult:
    version_id: str
    skill_id: str
    decision_id: str
    decision: str
    actor: str
    rationale: str
    governance_status: str
    version_status: str
    can_execute: bool = False
    can_approve: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def record_human_decision(
    version_id: str,
    decision: str,
    actor: str,
    rationale: str = "",
    session=None,
) -> HumanDecisionResult:
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return HumanDecisionResult(
            version_id=version_id,
            skill_id="",
            decision_id="",
            decision=decision,
            actor=actor,
            rationale=rationale,
            governance_status="blocked",
            version_status="not_found",
            blocking_reason="version_not_found",
        )

    validation = validate_human_decision(decision, actor, rationale)
    if not validation.valid:
        return HumanDecisionResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            decision_id="",
            decision=decision,
            actor=actor,
            rationale=rationale,
            governance_status="blocked",
            version_status=version_row.status,
            blocking_reason="; ".join(validation.issues),
        )

    governance_status = _GOVERNANCE_STATUS.get(decision, "unknown")

    decision_row = create_agent_candidate_decision(
        session,
        version_id=version_id,
        decision=decision,
        actor=actor,
        rationale=rationale,
        detail_json=json.dumps({
            "governance_status": governance_status,
            "version_status": version_row.status,
            "skill_id": version_row.skill_id,
        }),
    )

    create_agent_candidate_decision_event(
        session, version_id, "human_decision_recorded", "completed",
        json.dumps({
            "decision_id": decision_row.id,
            "decision": decision,
            "actor": actor,
            "governance_status": governance_status,
        }),
    )

    return HumanDecisionResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        decision_id=decision_row.id,
        decision=decision,
        actor=actor,
        rationale=rationale,
        governance_status=governance_status,
        version_status=version_row.status,
    )
