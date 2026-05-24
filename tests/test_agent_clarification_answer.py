from __future__ import annotations

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    list_clarification_answers_for_proposal,
)
from erpguard.product.agent_clarification_answer import (
    QuestionAnswer,
    SubmitAnswersRequest,
    submit_answers,
)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_proposal(session):
    sess = create_advisory_session(session, created_by_actor_json="{}")
    qs = [
        {"question_id": "q1", "question": "Trigger?", "answer_type": "choice"},
        {"question_id": "q2", "question": "Approver?", "answer_type": "text"},
    ]
    return create_advisory_proposal(
        session,
        session_id=sess.id,
        request_text="test",
        intent_json="{}",
        process_category="sales_cycle",
        entity_mappings_json="[]",
        workflow_json="{}",
        guards_json="{}",
        risk_summary_json="{}",
        clarification_questions_json=json.dumps(qs),
        revision_number=1,
        status="draft",
    )


def test_submit_valid_answers(session):
    proposal = _make_proposal(session)
    req = SubmitAnswersRequest(answers=[
        QuestionAnswer(question_id="q1", answer_text="scheduled"),
        QuestionAnswer(question_id="q2", answer_text="sales manager"),
    ])
    result = submit_answers(proposal.id, req, session)
    assert result.total_submitted == 2
    assert "q1" in result.submitted
    assert "q2" in result.submitted
    assert result.skipped_unknown == []


def test_submit_unknown_question_id_skipped(session):
    proposal = _make_proposal(session)
    req = SubmitAnswersRequest(answers=[
        QuestionAnswer(question_id="q99", answer_text="whatever"),
    ])
    result = submit_answers(proposal.id, req, session)
    assert result.total_submitted == 0
    assert "q99" in result.skipped_unknown


def test_submit_empty_answer_text_skipped(session):
    proposal = _make_proposal(session)
    req = SubmitAnswersRequest(answers=[
        QuestionAnswer(question_id="q1", answer_text="   "),
    ])
    result = submit_answers(proposal.id, req, session)
    assert result.total_submitted == 0


def test_submitted_answers_persisted(session):
    proposal = _make_proposal(session)
    req = SubmitAnswersRequest(answers=[
        QuestionAnswer(question_id="q1", answer_text="manual"),
    ])
    submit_answers(proposal.id, req, session)
    rows = list_clarification_answers_for_proposal(session, proposal.id)
    assert len(rows) == 1
    assert rows[0].answer_text == "manual"


def test_submit_to_unknown_proposal(session):
    req = SubmitAnswersRequest(answers=[QuestionAnswer(question_id="q1", answer_text="x")])
    result = submit_answers("missing_id", req, session)
    assert result.total_submitted == 0


def test_submit_is_advisory_only(session):
    proposal = _make_proposal(session)
    req = SubmitAnswersRequest(answers=[QuestionAnswer(question_id="q1", answer_text="scheduled")])
    result = submit_answers(proposal.id, req, session)
    assert result.is_advisory_only is True
    assert result.can_execute is False


def test_audit_event_created_on_submit(session):
    from erpguard.db.repositories import list_clarification_audit_events_for_proposal
    proposal = _make_proposal(session)
    req = SubmitAnswersRequest(answers=[QuestionAnswer(question_id="q1", answer_text="scheduled")])
    submit_answers(proposal.id, req, session)
    events = list_clarification_audit_events_for_proposal(session, proposal.id)
    assert any(e.event_type == "answers_submitted" for e in events)
