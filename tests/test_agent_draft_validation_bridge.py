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
from erpguard.product.agent_draft_validation_bridge import validate_agent_draft


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


def _make_draft(session, proposal_id="", guards=None, write_actions=False, runtime_mode="dry_run_only"):
    if guards is None:
        guards = {
            "mandatory_guards": [
                {"guard_id": "no_generic_writes"},
                {"guard_id": "no_r3_r4_writes"},
                {"guard_id": "no_raw_tool_execution"},
                {"guard_id": "requires_human_review"},
            ]
        }
    draft_content = {
        "source": "agent_advisory_proposal",
        "proposal_id": proposal_id,
        "runtime_mode": runtime_mode,
        "write_actions": write_actions,
        "guards": guards,
        "safety": {
            "runtime_mode": runtime_mode,
            "write_actions": write_actions,
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
        runtime_mode=runtime_mode,
        write_actions=write_actions,
        draft_json=json.dumps(draft_content),
    )


def test_validation_passes_valid_agent_draft():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = validate_agent_draft(draft.id, session)
    assert result.validation_passed is True
    assert result.guard_normalization_applied is True
    assert result.can_execute is False


def test_validation_draft_not_found():
    session = _make_session()
    result = validate_agent_draft("nonexistent", session)
    assert result.validation_passed is False
    assert any(i.code == "draft_not_found" for i in result.issues)


def test_validation_write_actions_blocked():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id, write_actions=True)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = validate_agent_draft(draft.id, session)
    assert result.validation_passed is False
    assert any(i.code == "write_actions_enabled" for i in result.issues)


def test_validation_invalid_runtime_mode():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id, runtime_mode="live")
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = validate_agent_draft(draft.id, session)
    assert result.validation_passed is False
    assert any("runtime_mode" in i.code for i in result.issues)


def test_validation_missing_guards_flagged():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id, guards={"mandatory_guards": []})
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = validate_agent_draft(draft.id, session)
    assert result.validation_passed is False
    assert any("guard" in i.code for i in result.issues)


def test_guard_normalization_replaces_odoo_writes_check():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = validate_agent_draft(draft.id, session)
    assert result.guard_normalization_applied is True
    assert not any(i.code == "missing_no_odoo_writes_guard" for i in result.issues)


def test_safety_constants():
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = validate_agent_draft(draft.id, session)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_validation_audit_event_created():
    from erpguard.db.repositories import list_agent_draft_bridge_events_for_draft
    session = _make_session()
    adv = _make_advisory_session(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    validate_agent_draft(draft.id, session)
    events = list_agent_draft_bridge_events_for_draft(session, draft.id)
    assert len(events) >= 1
    assert events[-1].step == "validation"
