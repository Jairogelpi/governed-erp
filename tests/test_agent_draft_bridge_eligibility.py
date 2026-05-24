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
from erpguard.product.agent_draft_bridge_eligibility import check_bridge_eligibility


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_advisory_session(session):
    return create_advisory_session(session, created_by_actor_json="{}")


def _make_proposal(session, adv_session):
    return create_advisory_proposal(
        session,
        session_id=adv_session.id,
        request_text="Test",
        intent_json=json.dumps({"action_type": "read", "target_entity": "sale.order"}),
        process_category="sales_cycle",
        entity_mappings_json="[]",
        workflow_json=json.dumps({"steps": [{"id": "s1", "description": "read orders"}]}),
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
        "safety": {
            "runtime_mode": "dry_run_only",
            "write_actions": False,
            "can_execute": False,
            "is_advisory_only": True,
        },
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


def test_eligible_agent_draft():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal_id=proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = check_bridge_eligibility(draft.id, session)
    assert result.eligible is True
    assert result.is_agent_draft is True
    assert result.proposal_id == proposal.id
    assert result.issues == []


def test_draft_not_found():
    session = _make_session()
    result = check_bridge_eligibility("nonexistent_draft", session)
    assert result.eligible is False
    assert any(i.code == "draft_not_found" for i in result.issues)


def test_not_agent_draft():
    session = _make_session()
    draft = _make_draft(session, source="manual")
    result = check_bridge_eligibility(draft.id, session)
    assert result.eligible is False
    assert result.is_agent_draft is False
    assert any(i.code == "not_agent_draft" for i in result.issues)


def test_no_proposal_link():
    session = _make_session()
    draft = _make_draft(session)
    result = check_bridge_eligibility(draft.id, session)
    assert result.eligible is False
    assert any(i.code == "no_proposal_link" for i in result.issues)


def test_write_actions_blocked():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft_content = {"source": "agent_advisory_proposal", "safety": {"can_execute": False}}
    draft = create_automation_draft(
        session,
        opportunity_id="x", scan_id="x", snapshot_id="x", connection_id="x",
        name="bad", description="bad", status="pending_review",
        runtime_mode="dry_run_only", write_actions=True,
        draft_json=json.dumps(draft_content),
    )
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)
    result = check_bridge_eligibility(draft.id, session)
    assert result.eligible is False
    assert any(i.code == "write_actions_enabled" for i in result.issues)


def test_invalid_runtime_mode():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft_content = {"source": "agent_advisory_proposal", "safety": {"can_execute": False}}
    draft = create_automation_draft(
        session,
        opportunity_id="x", scan_id="x", snapshot_id="x", connection_id="x",
        name="bad", description="bad", status="pending_review",
        runtime_mode="live", write_actions=False,
        draft_json=json.dumps(draft_content),
    )
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)
    result = check_bridge_eligibility(draft.id, session)
    assert result.eligible is False
    assert any(i.code == "invalid_runtime_mode" for i in result.issues)


def test_can_execute_flag_blocked():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft_content = {"source": "agent_advisory_proposal", "safety": {"can_execute": True}}
    draft = create_automation_draft(
        session,
        opportunity_id="x", scan_id="x", snapshot_id="x", connection_id="x",
        name="bad", description="bad", status="pending_review",
        runtime_mode="dry_run_only", write_actions=False,
        draft_json=json.dumps(draft_content),
    )
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)
    result = check_bridge_eligibility(draft.id, session)
    assert result.eligible is False
    assert any(i.code == "execution_flag_set" for i in result.issues)


def test_safety_constants_always_enforced():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal_id=proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)
    result = check_bridge_eligibility(draft.id, session)
    assert result.can_execute is False
    assert result.write_actions is False
    assert result.runtime_mode == "dry_run_only"
    assert result.is_advisory_only is True
