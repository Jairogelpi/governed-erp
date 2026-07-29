from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_skill_approval_decision,
    get_latest_approval_request_for_skill,
    list_approval_decisions_for_skill,
    update_approval_request_status,
)
from erpguard.product.models import ApprovalDecisionModel

_ALLOWED_DECISIONS = {"approve", "reject", "request_changes"}


class ApprovalDecisionService:
    def __init__(self, session) -> None:
        self.session = session

    def decide(self, skill_id: str, decided_by: dict, decision: str, reason: str) -> ApprovalDecisionModel:
        if decision not in _ALLOWED_DECISIONS:
            raise ValueError(f"Decision '{decision}' is not valid. Must be one of: {sorted(_ALLOWED_DECISIONS)}.")

        req = get_latest_approval_request_for_skill(self.session, skill_id)
        if req is None:
            raise ObjectNotFoundError(f"No pending approval request found for skill '{skill_id}'.")
        if req.status not in ("pending", "under_review"):
            raise ValueError(f"Approval request '{req.id}' has status '{req.status}' and cannot receive a new decision.")

        evidence = {
            "approval_request_id": req.id,
            "skill_id": skill_id,
            "decision": decision,
            "can_execute_real_writes": False,
            "approved_for_real_execution": False,
            "governance_note": "Approval only authorizes dry-run governance state. Real execution is not enabled.",
        }

        new_status = {
            "approve": "approved_for_dry_run",
            "reject": "rejected",
            "request_changes": "changes_requested",
        }[decision]

        row = create_skill_approval_decision(
            self.session,
            approval_request_id=req.id,
            skill_id=skill_id,
            decided_by_json=json.dumps(decided_by, default=str),
            decision=decision,
            reason=reason,
            evidence_json=json.dumps(evidence, default=str),
        )
        update_approval_request_status(self.session, req.id, new_status)

        return ApprovalDecisionModel.model_validate(
            {
                "decision_id": row.id,
                "approval_request_id": row.approval_request_id,
                "skill_id": row.skill_id,
                "decided_by": decided_by,
                "decision": row.decision,
                "reason": row.reason,
                "can_execute_real_writes": False,
                "approved_for_real_execution": False,
                "evidence": evidence,
                "created_at": row.created_at.isoformat(),
            }
        )

    def list_history(self, skill_id: str) -> list[ApprovalDecisionModel]:
        rows = list_approval_decisions_for_skill(self.session, skill_id)
        history: list[ApprovalDecisionModel] = []
        for row in rows:
            history.append(
                ApprovalDecisionModel.model_validate(
                    {
                        "decision_id": row.id,
                        "approval_request_id": row.approval_request_id,
                        "skill_id": row.skill_id,
                        "decided_by": json.loads(row.decided_by_json),
                        "decision": row.decision,
                        "reason": row.reason,
                        "can_execute_real_writes": False,
                        "approved_for_real_execution": False,
                        "evidence": json.loads(row.evidence_json),
                        "created_at": row.created_at.isoformat(),
                    }
                )
            )
        return history
