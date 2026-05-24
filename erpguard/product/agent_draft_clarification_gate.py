from __future__ import annotations

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_agent_proposal_draft_link_by_draft,
    get_automation_draft,
)
from erpguard.product.agent_clarification_completeness import compute_clarification_completeness

_QUESTIONS_THRESHOLD = 50
_MAPPINGS_THRESHOLD = 50


class ClarificationGateResult(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    gate_passed: bool
    questions_pct: int
    mappings_pct: int
    overall_complete: bool
    blocking_reasons: list[str] = Field(default_factory=list)
    can_execute: bool = False
    is_advisory_only: bool = True


def check_clarification_gate(draft_id: str, session: Session) -> ClarificationGateResult:
    draft = get_automation_draft(session, draft_id)
    if draft is None:
        return ClarificationGateResult(
            draft_id=draft_id,
            gate_passed=False,
            questions_pct=0,
            mappings_pct=0,
            overall_complete=False,
            blocking_reasons=["Draft not found"],
        )

    link = get_agent_proposal_draft_link_by_draft(session, draft_id)
    if link is None:
        return ClarificationGateResult(
            draft_id=draft_id,
            gate_passed=False,
            questions_pct=0,
            mappings_pct=0,
            overall_complete=False,
            blocking_reasons=["No linked proposal found for this draft"],
        )

    proposal_id = link.proposal_id
    completeness = compute_clarification_completeness(proposal_id, session)

    blocking_reasons: list[str] = []
    if completeness.questions_pct < _QUESTIONS_THRESHOLD:
        blocking_reasons.append(
            f"Questions answered: {completeness.questions_pct}% (threshold {_QUESTIONS_THRESHOLD}%)"
        )
    if completeness.mappings_total > 0 and completeness.mappings_pct < _MAPPINGS_THRESHOLD:
        blocking_reasons.append(
            f"Mappings confirmed: {completeness.mappings_pct}% (threshold {_MAPPINGS_THRESHOLD}%)"
        )

    gate_passed = len(blocking_reasons) == 0

    return ClarificationGateResult(
        draft_id=draft_id,
        proposal_id=proposal_id,
        gate_passed=gate_passed,
        questions_pct=completeness.questions_pct,
        mappings_pct=completeness.mappings_pct,
        overall_complete=completeness.overall_complete,
        blocking_reasons=blocking_reasons,
        can_execute=False,
        is_advisory_only=True,
    )
