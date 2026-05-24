from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
)

_AGENT_DRAFT_SOURCE = "agent_advisory_proposal"


class BridgeEligibilityIssue(BaseModel):
    code: str
    message: str
    severity: str = "blocking"


class BridgeEligibilityResult(BaseModel):
    draft_id: str
    eligible: bool
    is_agent_draft: bool
    proposal_id: str | None = None
    issues: list[BridgeEligibilityIssue] = Field(default_factory=list)
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def check_bridge_eligibility(draft_id: str, session: Session) -> BridgeEligibilityResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return BridgeEligibilityResult(
            draft_id=draft_id,
            eligible=False,
            is_agent_draft=False,
            issues=[BridgeEligibilityIssue(
                code="draft_not_found",
                message=f"AutomationDraft '{draft_id}' was not found.",
            )],
        )

    try:
        package = json.loads(draft.draft_json)
    except (json.JSONDecodeError, ValueError):
        return BridgeEligibilityResult(
            draft_id=draft_id,
            eligible=False,
            is_agent_draft=False,
            issues=[BridgeEligibilityIssue(
                code="invalid_draft_json",
                message="Draft package JSON is malformed.",
            )],
        )

    is_agent_draft = package.get("source") == _AGENT_DRAFT_SOURCE
    proposal_id: str | None = None
    issues: list[BridgeEligibilityIssue] = []

    if not is_agent_draft:
        issues.append(BridgeEligibilityIssue(
            code="not_agent_draft",
            message=f"Draft source is '{package.get('source')}'. Only agent advisory drafts can use the bridge pipeline.",
        ))

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    if link is not None:
        proposal_id = link.proposal_id
    else:
        issues.append(BridgeEligibilityIssue(
            code="no_proposal_link",
            message="Draft has no linked AdvisoryProposal. Bridge requires a proposal link.",
        ))

    if draft.write_actions:
        issues.append(BridgeEligibilityIssue(
            code="write_actions_enabled",
            message="Draft has write_actions=True. Bridge is only permitted for write_actions=False drafts.",
        ))

    if draft.runtime_mode != "dry_run_only":
        issues.append(BridgeEligibilityIssue(
            code="invalid_runtime_mode",
            message=f"Draft runtime_mode is '{draft.runtime_mode}'. Bridge requires 'dry_run_only'.",
        ))

    safety = package.get("safety", {})
    if safety.get("can_execute") is True:
        issues.append(BridgeEligibilityIssue(
            code="execution_flag_set",
            message="Draft safety.can_execute=True. Bridge is only permitted for advisory-only drafts.",
        ))

    return BridgeEligibilityResult(
        draft_id=draft_id,
        eligible=len(issues) == 0,
        is_agent_draft=is_agent_draft,
        proposal_id=proposal_id,
        issues=issues,
        runtime_mode="dry_run_only",
        write_actions=False,
        can_execute=False,
        is_advisory_only=True,
    )
