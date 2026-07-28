import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    create_agent_proposal_draft_link,
    create_automation_draft,
)
from erpguard.product.agent_draft_review_bridge import bridge_to_review


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_advisory_session(session):
    return create_advisory_session(session, created_by_actor_json="{}")


def _make_proposal(session, adv):
    return create_advisory_proposal(
        session,
        session_id=adv.id,
        request_text="Test",
        intent_json=json.dumps({"action_type": "read", "target_entity": "sale.order"}),
        process_category="sales_cycle",
        entity_mappings_json="[]",
        workflow_json=json.dumps({"steps": [{"id": "s1", "description": "read orders"}]}),
        guards_json="{}",
        risk_summary_json="{}",
        clarification_questions_json="[]",
    )


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


def test_bridge_to_review_creates_review():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = bridge_to_review(draft.id, session)
    assert result.bridged is True
    assert result.review_id is not None
    assert result.guards_count > 0
    assert result.test_cases_count > 0


def test_bridge_to_review_idempotent():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    r1 = bridge_to_review(draft.id, session)
    r2 = bridge_to_review(draft.id, session)
    assert r1.review_id == r2.review_id
    assert r2.bridged is True


def test_bridge_draft_not_found():
    session = _make_session()
    result = bridge_to_review("nonexistent", session)
    assert result.bridged is False
    assert result.blocking_reason == "draft_not_found"


def test_bridge_no_proposal_link():
    session = _make_session()
    draft = _make_draft(session)
    result = bridge_to_review(draft.id, session)
    assert result.bridged is False
    assert result.blocking_reason == "no_proposal_link"


def test_bridge_safety_constants():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = bridge_to_review(draft.id, session)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_bridge_proposal_id_in_result():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = bridge_to_review(draft.id, session)
    assert result.proposal_id == proposal.id


def test_bridge_audit_event_created():
    from erpguard.db.repositories import list_agent_draft_bridge_events_for_draft
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    bridge_to_review(draft.id, session)
    events = list_agent_draft_bridge_events_for_draft(session, draft.id)
    assert len(events) >= 1
    assert events[-1].step == "review"
    assert events[-1].status == "passed"
