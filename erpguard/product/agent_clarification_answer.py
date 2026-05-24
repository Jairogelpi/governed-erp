from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_clarification_answer,
    create_clarification_audit_event,
    get_advisory_proposal,
    get_latest_clarification_answer_for_question,
)


class QuestionAnswer(BaseModel):
    question_id: str
    answer_text: str


class SubmitAnswersRequest(BaseModel):
    answers: list[QuestionAnswer] = Field(default_factory=list)


class AnswerResult(BaseModel):
    proposal_id: str
    submitted: list[str] = Field(default_factory=list)
    skipped_unknown: list[str] = Field(default_factory=list)
    total_submitted: int = 0
    is_advisory_only: bool = True
    can_execute: bool = False


def submit_answers(
    proposal_id: str,
    request: SubmitAnswersRequest,
    session: Session,
) -> AnswerResult:
    proposal = get_advisory_proposal(session, proposal_id)
    if proposal is None:
        return AnswerResult(proposal_id=proposal_id)

    raw_questions = json.loads(proposal.clarification_questions_json or "[]")
    valid_ids = {q["question_id"] for q in raw_questions if "question_id" in q}

    submitted: list[str] = []
    skipped: list[str] = []

    for qa in request.answers:
        if qa.question_id not in valid_ids:
            skipped.append(qa.question_id)
            continue
        if not qa.answer_text.strip():
            skipped.append(qa.question_id)
            continue
        create_clarification_answer(
            session,
            proposal_id=proposal_id,
            question_id=qa.question_id,
            answer_text=qa.answer_text.strip(),
        )
        submitted.append(qa.question_id)

    if submitted:
        create_clarification_audit_event(
            session,
            proposal_id=proposal_id,
            event_type="answers_submitted",
            detail_json=json.dumps({"submitted": submitted, "skipped": skipped}),
        )

    return AnswerResult(
        proposal_id=proposal_id,
        submitted=submitted,
        skipped_unknown=skipped,
        total_submitted=len(submitted),
        is_advisory_only=True,
        can_execute=False,
    )
