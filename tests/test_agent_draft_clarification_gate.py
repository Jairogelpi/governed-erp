import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    create_agent_proposal_draft_link,
    create_automation_draft,
    create_clarification_answer,
)
from erpguard.product.agent_draft_clarification_gate import check_clarification_gate


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_draft(session, proposal_id=""):
    draft_content = {
        "source": "agent_advisory_proposal",
        "proposal_id": proposal_id,
        "safety": {"can_execute": False, "is_advisory_only": True},
    }
    return create_automation_draft(
        session,
        opportunity_id=f"agent_proposal:{proposal_id}",
        scan_id="agent_advisory",
        snapshot_id="agent_advisory",
        connection_id="agent_advisory",
        name="Test Draft",
        description="test",
        status="pending_review",
        runtime_mode="dry_run_only",
        write_actions=False,
        draft_json=json.dumps(draft_content),
    )


def _make_proposal_with_questions(session, adv_session_id, questions):
    return create_advisory_proposal(
        session,
        session_id=adv_session_id,
        request_text="Test",
        intent_json=json.dumps({"action_type": "read", "target_entity": "sale.order"}),
        process_category="sales_cycle",
        entity_mappings_json="[]",
        workflow_json=json.dumps({"steps": [{"id": "s1"}]}),
        guards_json="{}",
        risk_summary_json="{}",
        clarification_questions_json=json.dumps(questions),
    )


def test_gate_passes_no_questions():
    session = _make_session()
    adv = create_advisory_session(session, created_by_actor_json="{}")
    proposal = _make_proposal_with_questions(session, adv.id, [])
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = check_clarification_gate(draft.id, session)
    assert result.gate_passed is True
    assert result.questions_pct == 100


def test_gate_passes_all_answered():
    session = _make_session()
    adv = create_advisory_session(session, created_by_actor_json="{}")
    questions = [{"question_id": "q1", "question": "When?", "answer_type": "text"}]
    proposal = _make_proposal_with_questions(session, adv.id, questions)
    create_clarification_answer(session, proposal.id, "q1", "Monday")
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = check_clarification_gate(draft.id, session)
    assert result.gate_passed is True
    assert result.questions_pct == 100


def test_gate_fails_no_answers_for_questions():
    session = _make_session()
    adv = create_advisory_session(session, created_by_actor_json="{}")
    questions = [
        {"question_id": "q1", "question": "When?", "answer_type": "text"},
        {"question_id": "q2", "question": "Why?", "answer_type": "text"},
    ]
    proposal = _make_proposal_with_questions(session, adv.id, questions)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = check_clarification_gate(draft.id, session)
    assert result.gate_passed is False
    assert len(result.blocking_reasons) > 0


def test_gate_no_link():
    session = _make_session()
    draft = _make_draft(session)
    result = check_clarification_gate(draft.id, session)
    assert result.gate_passed is False
    assert any("No linked proposal" in r for r in result.blocking_reasons)


def test_gate_draft_not_found():
    session = _make_session()
    result = check_clarification_gate("nonexistent", session)
    assert result.gate_passed is False
    assert any("not found" in r.lower() for r in result.blocking_reasons)


def test_safety_constants():
    session = _make_session()
    adv = create_advisory_session(session, created_by_actor_json="{}")
    proposal = _make_proposal_with_questions(session, adv.id, [])
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = check_clarification_gate(draft.id, session)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_gate_partial_answers_below_threshold():
    session = _make_session()
    adv = create_advisory_session(session, created_by_actor_json="{}")
    questions = [
        {"question_id": f"q{i}", "question": f"Q{i}?", "answer_type": "text"}
        for i in range(1, 5)
    ]
    proposal = _make_proposal_with_questions(session, adv.id, questions)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = check_clarification_gate(draft.id, session)
    assert result.questions_pct == 0
    assert result.gate_passed is False
