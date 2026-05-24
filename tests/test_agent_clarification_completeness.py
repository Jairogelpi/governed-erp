from __future__ import annotations

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    create_clarification_answer,
    create_mapping_confirmation,
)
from erpguard.product.agent_clarification_completeness import compute_clarification_completeness


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_proposal(session, questions=None, mappings=None):
    adv_session = create_advisory_session(session, created_by_actor_json="{}")
    qs = questions or [
        {"question_id": "q1", "question": "Trigger?", "answer_type": "choice"},
    ]
    ms = mappings or [
        {"field": "state", "odoo_field": "state", "odoo_model": "sale.order", "required": True},
    ]
    return create_advisory_proposal(
        session,
        session_id=adv_session.id,
        request_text="test",
        intent_json="{}",
        process_category="sales_cycle",
        entity_mappings_json=json.dumps(ms),
        workflow_json="{}",
        guards_json="{}",
        risk_summary_json="{}",
        clarification_questions_json=json.dumps(qs),
        revision_number=1,
        status="draft",
    )


def test_completeness_nothing_done(session):
    proposal = _make_proposal(session)
    result = compute_clarification_completeness(proposal.id, session)
    assert result.questions_answered == 0
    assert result.questions_total == 1
    assert result.overall_complete is False


def test_completeness_all_answered(session):
    proposal = _make_proposal(session)
    create_clarification_answer(session, proposal.id, "q1", "scheduled")
    result = compute_clarification_completeness(proposal.id, session)
    assert result.questions_answered == 1
    assert result.overall_complete is True


def test_completeness_pct_calculation(session):
    qs = [
        {"question_id": "q1", "question": "A?", "answer_type": "text"},
        {"question_id": "q2", "question": "B?", "answer_type": "text"},
    ]
    proposal = _make_proposal(session, questions=qs)
    create_clarification_answer(session, proposal.id, "q1", "answer1")
    result = compute_clarification_completeness(proposal.id, session)
    assert result.questions_pct == 50


def test_mappings_confirmed_count(session):
    proposal = _make_proposal(session, questions=[])
    create_mapping_confirmation(session, proposal.id, "state", "confirmed")
    result = compute_clarification_completeness(proposal.id, session)
    assert result.mappings_confirmed == 1


def test_mappings_rejected_count(session):
    proposal = _make_proposal(session, questions=[])
    create_mapping_confirmation(session, proposal.id, "state", "rejected", "wrong")
    result = compute_clarification_completeness(proposal.id, session)
    assert result.mappings_rejected == 1


def test_next_steps_populated(session):
    proposal = _make_proposal(session)
    result = compute_clarification_completeness(proposal.id, session)
    assert len(result.next_steps) > 0


def test_completeness_is_advisory_only(session):
    proposal = _make_proposal(session)
    result = compute_clarification_completeness(proposal.id, session)
    assert result.is_advisory_only is True
    assert result.can_execute is False
