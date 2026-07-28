import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    create_agent_proposal_draft_link,
    create_agent_draft_bridge_event,
    create_automation_draft,
)
from erpguard.product.agent_draft_proof_evidence import get_proof_evidence


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_draft(session, proposal_id=""):
    draft_content = {
        "source": "agent_advisory_proposal",
        "proposal_id": proposal_id,
        "safety": {"can_execute": False},
    }
    return create_automation_draft(
        session,
        opportunity_id="agent_advisory",
        scan_id="agent_advisory",
        snapshot_id="agent_advisory",
        connection_id="agent_advisory",
        name="Test",
        description="test",
        status="pending_review",
        runtime_mode="dry_run_only",
        write_actions=False,
        draft_json=json.dumps(draft_content),
    )


def test_evidence_draft_not_found():
    session = _make_session()
    result = get_proof_evidence("nonexistent", session)
    assert result.blocking_reason == "draft_not_found"


def test_evidence_empty_no_bridge_events():
    session = _make_session()
    draft = _make_draft(session)
    result = get_proof_evidence(draft.id, session)
    assert result.bridge_steps_passed == 0
    assert result.bridge_steps_total == 3
    assert result.evidence_count > 0


def test_evidence_counts_bridge_events():
    session = _make_session()
    adv = create_advisory_session(session, created_by_actor_json="{}")
    proposal = create_advisory_proposal(
        session, session_id=adv.id, request_text="Test",
        intent_json="{}", process_category="general",
        entity_mappings_json="[]", workflow_json="{}", guards_json="{}",
        risk_summary_json="{}", clarification_questions_json="[]",
    )
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    create_agent_draft_bridge_event(session, draft.id, proposal.id, "review", "passed", "{}")
    create_agent_draft_bridge_event(session, draft.id, proposal.id, "validation", "passed", "{}")

    result = get_proof_evidence(draft.id, session)
    assert result.bridge_steps_passed == 2


def test_evidence_safety_constants():
    session = _make_session()
    draft = _make_draft(session)
    result = get_proof_evidence(draft.id, session)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_evidence_proof_plan_not_generated():
    session = _make_session()
    draft = _make_draft(session)
    result = get_proof_evidence(draft.id, session)
    assert result.proof_plan_generated is False


def test_evidence_proof_plan_detected():
    from erpguard.db.repositories import create_agent_draft_handoff_event
    session = _make_session()
    draft = _make_draft(session)
    create_agent_draft_handoff_event(session, draft.id, "x", "proof_plan", "passed", "{}")
    result = get_proof_evidence(draft.id, session)
    assert result.proof_plan_generated is True


def test_evidence_creates_handoff_event():
    from erpguard.db.repositories import list_agent_draft_handoff_events_for_draft
    session = _make_session()
    draft = _make_draft(session)
    get_proof_evidence(draft.id, session)
    events = list_agent_draft_handoff_events_for_draft(session, draft.id)
    assert any(ev.step == "evidence" for ev in events)
