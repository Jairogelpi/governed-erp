from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
    create_agent_draft_bridge_event,
)
from erpguard.product.draft_validator import DraftValidatorService

_AGENT_DRAFT_SOURCE = "agent_advisory_proposal"
_AGENT_GUARD_IDS = {"no_generic_writes", "no_r3_r4_writes", "no_raw_tool_execution", "requires_human_review"}
_NORMALIZED_GUARD_ISSUE = "missing_no_odoo_writes_guard"


class ValidationBridgeIssue(BaseModel):
    code: str
    message: str
    severity: str = "blocking"


class DraftValidationBridgeResult(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    validation_passed: bool
    issues: list[ValidationBridgeIssue] = Field(default_factory=list)
    guard_normalization_applied: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def validate_agent_draft(draft_id: str, session: Session) -> DraftValidationBridgeResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return DraftValidationBridgeResult(
            draft_id=draft_id,
            validation_passed=False,
            issues=[ValidationBridgeIssue(
                code="draft_not_found",
                message=f"AutomationDraft '{draft_id}' was not found.",
            )],
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    proposal_id = link.proposal_id if link else None

    try:
        package = json.loads(draft.draft_json)
    except (json.JSONDecodeError, ValueError):
        return DraftValidationBridgeResult(
            draft_id=draft_id,
            proposal_id=proposal_id,
            validation_passed=False,
            issues=[ValidationBridgeIssue(
                code="invalid_draft_json",
                message="Draft package JSON is malformed.",
            )],
        )

    is_agent_draft = package.get("source") == _AGENT_DRAFT_SOURCE
    guard_normalization_applied = False

    validator = DraftValidatorService(session)
    result = validator.validate(draft_id)

    issues: list[ValidationBridgeIssue] = []
    for issue in result.issues:
        if is_agent_draft and issue.code == _NORMALIZED_GUARD_ISSUE:
            guard_normalization_applied = True
            guards = package.get("guards", {})
            mandatory_guard_ids = {
                g.get("guard_id") for g in guards.get("mandatory_guards", [])
            }
            missing = _AGENT_GUARD_IDS - mandatory_guard_ids
            if missing:
                issues.append(ValidationBridgeIssue(
                    code="missing_agent_mandatory_guards",
                    message=f"Agent draft is missing mandatory guard(s): {sorted(missing)}.",
                    severity="blocking",
                ))
        else:
            issues.append(ValidationBridgeIssue(
                code=issue.code,
                message=issue.message,
                severity=issue.severity,
            ))

    validation_passed = len(issues) == 0

    create_agent_draft_bridge_event(
        session,
        draft_id,
        proposal_id or draft_id,
        "validation",
        "passed" if validation_passed else "failed",
        json.dumps({
            "issues_count": len(issues),
            "guard_normalization_applied": guard_normalization_applied,
        }),
    )

    return DraftValidationBridgeResult(
        draft_id=draft_id,
        proposal_id=proposal_id,
        validation_passed=validation_passed,
        issues=issues,
        guard_normalization_applied=guard_normalization_applied,
        can_execute=False,
        is_advisory_only=True,
    )
