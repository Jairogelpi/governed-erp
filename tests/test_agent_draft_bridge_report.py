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
)
from erpguard.product.agent_draft_bridge_report import get_bridge_report


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
        workflow_json=json.dumps({"steps": [{"id": "s1"}]}),
        guards_json=json.dumps({"mandatory_guards": [
            {"guard_id": "no_generic_writes"},
            {"guard_id": "no_r3_r4_writes"},
            {"guard_id": "no_raw_tool_execution"},
            {"guard_id": "requires_human_review"},
        ]}),
        risk_summary_json="{}",
        clarification_questions_json="[]",
    )


def _make_draft(session, proposal_id="", source="agent_advisory_proposal"):
    draft_content = {
        "source": source,
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


def test_report_draft_not_found():
    session = _make_session()
    result = get_bridge_report("nonexistent", session)
    assert result.overall_status == "blocked"
    assert any("not found" in s.detail.lower() for s in result.steps if s.detail)


def test_report_ineligible_draft():
    session = _make_session()
    draft = _make_draft(session, source="manual")
    result = get_bridge_report(draft.id, session)
    assert result.overall_status == "blocked"
    assert any(s.step == "eligibility" and s.status == "failed" for s in result.steps)


def test_report_eligible_no_steps_run():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = get_bridge_report(draft.id, session)
    assert result.overall_status == "incomplete"
    assert any(s.step == "eligibility" and s.status == "passed" for s in result.steps)
    assert any(s.status == "not_started" for s in result.steps)


def test_report_after_review_step():
    from erpguard.product.agent_draft_review_bridge import bridge_to_review
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    bridge_to_review(draft.id, session)
    result = get_bridge_report(draft.id, session)
    review_step = next((s for s in result.steps if s.step == "review"), None)
    assert review_step is not None
    assert review_step.status == "passed"


def test_report_safety_constants():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = get_bridge_report(draft.id, session)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_report_proposal_id_included():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = get_bridge_report(draft.id, session)
    assert result.proposal_id == proposal.id


def test_report_complete_after_all_steps():
    from erpguard.product.agent_draft_review_bridge import bridge_to_review
    from erpguard.product.agent_draft_validation_bridge import validate_agent_draft
    from erpguard.product.agent_draft_compile_bridge import generate_compile_plan
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)

    draft_content = {
        "source": "agent_advisory_proposal",
        "proposal_id": proposal.id,
        "runtime_mode": "dry_run_only",
        "write_actions": False,
        "guards": {"mandatory_guards": [
            {"guard_id": "no_generic_writes"},
            {"guard_id": "no_r3_r4_writes"},
            {"guard_id": "no_raw_tool_execution"},
            {"guard_id": "requires_human_review"},
        ]},
        "entity_mappings": [],
        "workflow": {"steps": [{"id": "s1"}]},
        "safety": {"can_execute": False, "is_advisory_only": True},
    }
    draft = create_automation_draft(
        session,
        opportunity_id=f"agent_proposal:{proposal.id}",
        scan_id="agent_advisory", snapshot_id="agent_advisory", connection_id="agent_advisory",
        name="Test", description="test", status="pending_review",
        runtime_mode="dry_run_only", write_actions=False,
        draft_json=json.dumps(draft_content),
    )
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    bridge_to_review(draft.id, session)
    validate_agent_draft(draft.id, session)
    generate_compile_plan(draft.id, session)

    result = get_bridge_report(draft.id, session)
    assert result.overall_status == "complete"
    assert "human review" in result.next_action.lower()
