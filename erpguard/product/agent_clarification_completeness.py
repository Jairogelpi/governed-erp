from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_advisory_proposal,
    list_clarification_answers_for_proposal,
    list_mapping_confirmations_for_proposal,
)
from erpguard.product.agent_mapping_completeness import check_mapping_completeness


class ClarificationCompletenessResult(BaseModel):
    proposal_id: str
    questions_total: int
    questions_answered: int
    questions_pct: int
    mappings_total: int
    mappings_confirmed: int
    mappings_rejected: int
    mappings_pct: int
    mapping_issues: list[str] = Field(default_factory=list)
    overall_complete: bool
    is_advisory_only: bool = True
    can_execute: bool = False
    next_steps: list[str] = Field(default_factory=list)


def compute_clarification_completeness(
    proposal_id: str,
    session: Session,
) -> ClarificationCompletenessResult:
    proposal = get_advisory_proposal(session, proposal_id)
    if proposal is None:
        return ClarificationCompletenessResult(
            proposal_id=proposal_id,
            questions_total=0,
            questions_answered=0,
            questions_pct=100,
            mappings_total=0,
            mappings_confirmed=0,
            mappings_rejected=0,
            mappings_pct=100,
            overall_complete=True,
            next_steps=["Create proposal first"],
        )

    raw_questions = json.loads(proposal.clarification_questions_json or "[]")
    questions_total = len(raw_questions)

    answers = list_clarification_answers_for_proposal(session, proposal_id)
    answered_ids = {a.question_id for a in answers}
    questions_answered = sum(
        1 for q in raw_questions if q.get("question_id", "") in answered_ids
    )
    questions_pct = (questions_answered * 100 // questions_total) if questions_total else 100

    proposal_dict = {
        "proposal_id": proposal_id,
        "entity_mappings": json.loads(proposal.entity_mappings_json or "[]"),
    }
    mapping_result = check_mapping_completeness(proposal_dict)
    mappings_total = len(json.loads(proposal.entity_mappings_json or "[]"))

    confirmations = list_mapping_confirmations_for_proposal(session, proposal_id)
    seen: dict[str, str] = {}
    for c in confirmations:
        seen[c.mapping_key] = c.action
    mappings_confirmed = sum(1 for a in seen.values() if a == "confirmed")
    mappings_rejected = sum(1 for a in seen.values() if a == "rejected")
    mappings_pct = (mappings_confirmed * 100 // mappings_total) if mappings_total else 100

    issues = [i.message for i in mapping_result.issues]
    next_steps: list[str] = []
    if questions_answered < questions_total:
        pending = questions_total - questions_answered
        next_steps.append(f"Answer {pending} pending clarification question(s)")
    if mappings_total > 0 and mappings_confirmed < mappings_total:
        unconfirmed = mappings_total - mappings_confirmed - mappings_rejected
        if unconfirmed > 0:
            next_steps.append(f"Confirm or reject {unconfirmed} unreviewed mapping(s)")
    if not next_steps:
        next_steps.append("All clarifications complete — ready for human review")

    overall_complete = (questions_answered >= questions_total) and mapping_result.complete

    return ClarificationCompletenessResult(
        proposal_id=proposal_id,
        questions_total=questions_total,
        questions_answered=questions_answered,
        questions_pct=questions_pct,
        mappings_total=mappings_total,
        mappings_confirmed=mappings_confirmed,
        mappings_rejected=mappings_rejected,
        mappings_pct=mappings_pct,
        mapping_issues=issues,
        overall_complete=overall_complete,
        is_advisory_only=True,
        can_execute=False,
        next_steps=next_steps,
    )
