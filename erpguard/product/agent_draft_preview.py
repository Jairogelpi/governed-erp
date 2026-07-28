from __future__ import annotations


from pydantic import BaseModel, Field

from erpguard.product.agent_draft_safety_policy import SafetyPolicyResult, enforce_draft_safety
from erpguard.product.agent_mapping_completeness import MappingCompletenessResult, check_mapping_completeness
from erpguard.product.agent_proposal_eligibility import EligibilityResult, check_eligibility
from erpguard.product.agent_proposal_to_draft import transform_proposal_to_draft


class DraftPreview(BaseModel):
    proposal_id: str
    eligible: bool
    eligibility: EligibilityResult
    mapping_completeness: MappingCompletenessResult
    safety_policy: SafetyPolicyResult
    draft_name: str
    draft_description: str
    draft_runtime_mode: str = "dry_run_only"
    draft_write_actions: bool = False
    draft_status: str = "pending_review"
    workflow_steps: list[dict] = Field(default_factory=list)
    guard_ids: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"
    ready_to_create: bool = False
    blocking_issues: list[str] = Field(default_factory=list)
    advisory_note: str = (
        "This is a non-persisted preview. "
        "Call create-draft to persist the AutomationDraft and enter the review pipeline."
    )


def preview_draft(proposal: dict) -> DraftPreview:
    proposal_id = proposal.get("proposal_id", "")

    eligibility = check_eligibility(proposal)
    completeness = check_mapping_completeness(proposal)
    transform = transform_proposal_to_draft(proposal)
    safety = enforce_draft_safety(transform, proposal)

    workflow = proposal.get("workflow", {})
    steps = workflow.get("steps", [])

    guards = proposal.get("guards", {})
    guard_ids = guards.get("all_guard_ids", [])

    risk_summary = proposal.get("risk_summary", {})
    risk_level = risk_summary.get("overall_risk_level", "unknown")

    blocking = []
    for issue in eligibility.issues:
        if issue.severity == "blocking":
            blocking.append(issue.message)
    for v in safety.violations:
        blocking.append(v.message)

    ready = eligibility.eligible and safety.passed and len(blocking) == 0

    return DraftPreview(
        proposal_id=proposal_id,
        eligible=eligibility.eligible,
        eligibility=eligibility,
        mapping_completeness=completeness,
        safety_policy=safety,
        draft_name=transform.name,
        draft_description=transform.description,
        draft_runtime_mode=transform.runtime_mode,
        draft_write_actions=transform.write_actions,
        draft_status=transform.status,
        workflow_steps=steps,
        guard_ids=guard_ids,
        risk_level=risk_level,
        ready_to_create=ready,
        blocking_issues=blocking,
    )
