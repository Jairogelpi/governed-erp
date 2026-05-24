from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    create_clarification_answer,
)
from erpguard.product.agent_clarification_state import get_clarification_state


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_proposal(session, questions=None):
    import json
    sess = create_advisory_session(session, created_by_actor_json="{}")
    qs = questions if questions is not None else [
        {"question_id": "q1", "question": "Trigger type?", "answer_type": "choice"},
        {"question_id": "q2", "question": "Approver role?", "answer_type": "text"},
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


def test_state_no_answers(session):
    proposal = _make_proposal(session)
    state = get_clarification_state(proposal.id, session)
    assert state.total_questions == 2
    assert state.answered_count == 0
    assert state.pending_count == 2
    assert state.all_answered is False


def test_state_one_answer(session):
    proposal = _make_proposal(session)
    create_clarification_answer(session, proposal.id, "q1", "scheduled")
    state = get_clarification_state(proposal.id, session)
    assert state.answered_count == 1
    assert state.pending_count == 1
    assert state.all_answered is False


def test_state_all_answered(session):
    proposal = _make_proposal(session)
    create_clarification_answer(session, proposal.id, "q1", "scheduled")
    create_clarification_answer(session, proposal.id, "q2", "sales manager")
    state = get_clarification_state(proposal.id, session)
    assert state.all_answered is True
    assert state.pending_count == 0


def test_state_answer_text_preserved(session):
    proposal = _make_proposal(session)
    create_clarification_answer(session, proposal.id, "q1", "event-driven")
    state = get_clarification_state(proposal.id, session)
    q1 = next(q for q in state.questions if q.question_id == "q1")
    assert q1.answered is True
    assert q1.answer_text == "event-driven"


def test_state_no_questions(session):
    proposal = _make_proposal(session, questions=[])
    state = get_clarification_state(proposal.id, session)
    assert state.total_questions == 0
    assert state.all_answered is True


def test_state_unknown_proposal(session):
    state = get_clarification_state("unknown_proposal_id", session)
    assert state.total_questions == 0
    assert state.all_answered is True


def test_state_is_advisory_only(session):
    proposal = _make_proposal(session)
    state = get_clarification_state(proposal.id, session)
    assert state.total_questions == 2
