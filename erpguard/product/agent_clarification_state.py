from __future__ import annotations

import json

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    get_advisory_proposal,
    list_clarification_answers_for_proposal,
)


class ClarificationQuestionSummary(BaseModel):
    question_id: str
    question: str
    answer_type: str
    answered: bool
    answer_text: str | None = None


class ClarificationState(BaseModel):
    proposal_id: str
    total_questions: int
    answered_count: int
    pending_count: int
    all_answered: bool
    questions: list[ClarificationQuestionSummary] = Field(default_factory=list)


def get_clarification_state(proposal_id: str, session: Session) -> ClarificationState:
    proposal = get_advisory_proposal(session, proposal_id)
    if proposal is None:
        return ClarificationState(
            proposal_id=proposal_id,
            total_questions=0,
            answered_count=0,
            pending_count=0,
            all_answered=True,
            questions=[],
        )

    raw_questions = json.loads(proposal.clarification_questions_json or "[]")
    answers = list_clarification_answers_for_proposal(session, proposal_id)
    answered_map: dict[str, str] = {}
    for ans in answers:
        answered_map[ans.question_id] = ans.answer_text

    summaries: list[ClarificationQuestionSummary] = []
    for q in raw_questions:
        qid = q.get("question_id", "")
        answered = qid in answered_map
        summaries.append(ClarificationQuestionSummary(
            question_id=qid,
            question=q.get("question", ""),
            answer_type=q.get("answer_type", "text"),
            answered=answered,
            answer_text=answered_map.get(qid),
        ))

    total = len(summaries)
    answered_count = sum(1 for s in summaries if s.answered)
    pending_count = total - answered_count

    return ClarificationState(
        proposal_id=proposal_id,
        total_questions=total,
        answered_count=answered_count,
        pending_count=pending_count,
        all_answered=(pending_count == 0),
        questions=summaries,
    )
