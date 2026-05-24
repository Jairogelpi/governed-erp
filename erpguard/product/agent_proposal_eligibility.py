from __future__ import annotations

from pydantic import BaseModel, Field


class EligibilityIssue(BaseModel):
    code: str
    message: str
    severity: str = "blocking"


class EligibilityResult(BaseModel):
    proposal_id: str
    eligible: bool
    issues: list[EligibilityIssue] = Field(default_factory=list)
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    requires_human_review: bool = True
    requires_approval: bool = True


_ELIGIBLE_STATUSES = {"draft", "revised"}
_ELIGIBLE_PROCESS_CATEGORIES = {
    "sales_cycle", "purchase_cycle", "accounting_cycle",
    "inventory_management", "customer_management", "product_management",
    "reporting", "general",
}
_MANDATORY_GUARD_IDS = {
    "no_generic_writes", "no_r3_r4_writes",
    "no_raw_tool_execution", "requires_human_review",
}


def check_eligibility(proposal: dict) -> EligibilityResult:
    proposal_id = proposal.get("proposal_id", "")
    issues: list[EligibilityIssue] = []

    status = proposal.get("status", "")
    if status not in _ELIGIBLE_STATUSES:
        issues.append(EligibilityIssue(
            code="ineligible_status",
            message=f"Proposal status '{status}' is not eligible. Must be 'draft' or 'revised'.",
        ))

    intent = proposal.get("intent", {})
    if not intent or intent.get("action_type", "unknown") == "unknown":
        issues.append(EligibilityIssue(
            code="no_intent",
            message="Proposal has no recognised intent (action_type is unknown).",
        ))

    workflow = proposal.get("workflow", {})
    steps = workflow.get("steps", [])
    if not steps:
        issues.append(EligibilityIssue(
            code="empty_workflow",
            message="Proposal workflow has no steps.",
        ))

    guards = proposal.get("guards", {})
    mandatory_ids = {g.get("guard_id") for g in guards.get("mandatory_guards", [])}
    missing = _MANDATORY_GUARD_IDS - mandatory_ids
    if missing:
        issues.append(EligibilityIssue(
            code="missing_mandatory_guards",
            message=f"Proposal is missing mandatory guards: {sorted(missing)}.",
        ))

    if proposal.get("can_execute") is True:
        issues.append(EligibilityIssue(
            code="execution_flag_set",
            message="Proposal has can_execute=true. Only advisory proposals can be promoted to draft.",
        ))

    return EligibilityResult(
        proposal_id=proposal_id,
        eligible=len(issues) == 0,
        issues=issues,
        runtime_mode="dry_run_only",
        write_actions=False,
        requires_human_review=True,
        requires_approval=True,
    )
