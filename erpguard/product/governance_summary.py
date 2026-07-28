from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    get_latest_approval_request_for_skill,
    get_latest_gate_evaluation,
    get_skill,
    list_approval_decisions_for_skill,
)
from erpguard.product.models import (
    ActivationGateModel,
    ApprovalDecisionModel,
    ApprovalRequestModel,
    GovernanceSummaryModel,
)


def _governance_state(approval_req, decisions, gate) -> tuple[str, str]:
    if approval_req is None:
        return "not_submitted", "Submit an approval request to start the governance workflow."
    if not decisions:
        return "awaiting_decision", "Approval request submitted. Awaiting a human decision."
    approved = next((d for d in decisions if d.decision == "approve"), None)
    rejected = next((d for d in decisions if d.decision == "reject"), None)
    changes = next((d for d in decisions if d.decision == "request_changes"), None)
    if rejected:
        return "rejected", "Skill was rejected. Review the feedback and resubmit if appropriate."
    if changes:
        return "changes_requested", "Changes were requested. Address the feedback and resubmit."
    if approved:
        if gate and gate.gate_status == "open":
            return "approved_dry_run_only", "Approved for dry-run governance state. Real execution remains blocked."
        return "approved_pending_gate", "Approved. Run the activation gate to confirm all checks pass."
    return "awaiting_decision", "Approval request submitted. Awaiting a human decision."


class GovernanceSummaryService:
    def __init__(self, session) -> None:
        self.session = session

    def summarize(self, skill_id: str) -> GovernanceSummaryModel:
        skill_row = get_skill(self.session, skill_id)
        if skill_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' was not found.")

        approval_req_row = get_latest_approval_request_for_skill(self.session, skill_id)
        decision_rows = list_approval_decisions_for_skill(self.session, skill_id)
        gate_row = get_latest_gate_evaluation(self.session, skill_id)

        approval_req: ApprovalRequestModel | None = None
        if approval_req_row:
            approval_req = ApprovalRequestModel.model_validate(
                {
                    "request_id": approval_req_row.id,
                    "skill_id": approval_req_row.skill_id,
                    "skill_version_id": approval_req_row.skill_version_id,
                    "requested_by": json.loads(approval_req_row.requested_by_json),
                    "reason": approval_req_row.reason,
                    "status": approval_req_row.status,
                    "can_execute_real_writes": False,
                    "context": json.loads(approval_req_row.context_json),
                    "created_at": approval_req_row.created_at.isoformat(),
                }
            )

        decisions: list[ApprovalDecisionModel] = []
        for row in decision_rows:
            decisions.append(
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

        gate: ActivationGateModel | None = None
        if gate_row:
            gate = ActivationGateModel.model_validate(
                {
                    "gate_id": gate_row.id,
                    "skill_id": gate_row.skill_id,
                    "approval_request_id": gate_row.approval_request_id,
                    "gate_status": gate_row.gate_status,
                    "can_activate": gate_row.can_activate,
                    "can_execute_real_writes": False,
                    "approved_for_real_execution": False,
                    "checks": json.loads(gate_row.checks_json),
                    "created_at": gate_row.created_at.isoformat(),
                }
            )

        governance_state, next_action = _governance_state(approval_req, decisions, gate)

        return GovernanceSummaryModel.model_validate(
            {
                "skill_id": skill_id,
                "skill_name": skill_row.name,
                "skill_status": skill_row.status,
                "can_execute_real_writes": False,
                "approved_for_real_execution": False,
                "approval_request": approval_req.model_dump() if approval_req else None,
                "latest_decision": decisions[0].model_dump() if decisions else None,
                "latest_gate": gate.model_dump() if gate else None,
                "approval_history": [d.model_dump() for d in decisions],
                "governance_state": governance_state,
                "next_required_action": next_action,
                "created_at": skill_row.created_at.isoformat(),
            }
        )
