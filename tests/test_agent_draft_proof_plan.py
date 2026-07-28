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
from erpguard.product.agent_draft_proof_plan import generate_proof_plan


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_adv(session):
    return create_advisory_session(session, created_by_actor_json="{}")


def _make_proposal(session, adv):
    return create_advisory_proposal(
        session,
        session_id=adv.id,
        request_text="Test",
        intent_json=json.dumps({"action_type": "read", "target_entity": "sale.order"}),
        process_category="sales_cycle",
        entity_mappings_json=json.dumps([{"erp_field": "partner_id", "required": True}]),
        workflow_json=json.dumps({"steps": [
            {"id": "s1", "description": "read open orders"},
            {"id": "s2", "description": "aggregate by partner"},
        ]}),
        guards_json=json.dumps({"mandatory_guards": [
            {"guard_id": "no_generic_writes"},
            {"guard_id": "requires_human_review"},
        ]}),
        risk_summary_json="{}",
        clarification_questions_json="[]",
    )


def _make_draft(session, proposal_id="", write_actions=False, runtime_mode="dry_run_only"):
    draft_content = {
        "source": "agent_advisory_proposal",
        "proposal_id": proposal_id,
        "runtime_mode": runtime_mode,
        "write_actions": write_actions,
        "entity_mappings": [{"erp_field": "partner_id", "required": True}],
        "workflow": {"steps": [
            {"id": "s1", "description": "read open orders"},
            {"id": "s2", "description": "aggregate by partner"},
        ]},
        "guards": {"mandatory_guards": [
            {"guard_id": "no_generic_writes"},
            {"guard_id": "requires_human_review"},
        ]},
        "safety": {"can_execute": False, "is_advisory_only": True},
    }
    return create_automation_draft(
        session,
        opportunity_id="agent_advisory",
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


def test_proof_plan_generates_scenarios():
    session = _make_session()
    adv = _make_adv(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = generate_proof_plan(draft.id, session)
    assert result.plan_generated is True
    assert result.scenario_count > 0
    assert len(result.scenarios) == result.scenario_count


def test_proof_plan_covers_workflow_steps():
    session = _make_session()
    adv = _make_adv(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = generate_proof_plan(draft.id, session)
    workflow_scenarios = [s for s in result.scenarios if s.category == "workflow_dry_run"]
    assert len(workflow_scenarios) == 2


def test_proof_plan_covers_guards():
    session = _make_session()
    adv = _make_adv(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = generate_proof_plan(draft.id, session)
    guard_scenarios = [s for s in result.scenarios if s.category == "guard_check"]
    assert len(guard_scenarios) == 2


def test_proof_plan_draft_not_found():
    session = _make_session()
    result = generate_proof_plan("nonexistent", session)
    assert result.plan_generated is False
    assert result.blocking_reason == "draft_not_found"


def test_proof_plan_blocked_write_actions():
    session = _make_session()
    draft = _make_draft(session, write_actions=True)
    result = generate_proof_plan(draft.id, session)
    assert result.plan_generated is False
    assert "write_actions_enabled" in result.blocking_reason


def test_proof_plan_blocked_invalid_runtime():
    session = _make_session()
    draft = _make_draft(session, runtime_mode="live")
    result = generate_proof_plan(draft.id, session)
    assert result.plan_generated is False
    assert "invalid_runtime_mode" in result.blocking_reason


def test_proof_plan_safety_constants():
    session = _make_session()
    adv = _make_adv(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = generate_proof_plan(draft.id, session)
    assert result.can_execute is False
    assert result.is_advisory_only is True
    assert result.proof_is_plan_only is True
    assert "advisory only" in result.safety_note.lower()


def test_proof_plan_all_scenarios_plan_only():
    session = _make_session()
    adv = _make_adv(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    result = generate_proof_plan(draft.id, session)
    for scenario in result.scenarios:
        assert scenario.status == "plan_only"


def test_proof_plan_creates_audit_event():
    from erpguard.db.repositories import list_agent_draft_handoff_events_for_draft
    session = _make_session()
    adv = _make_adv(session)
    proposal = _make_proposal(session, adv)
    draft = _make_draft(session, proposal.id)
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)

    generate_proof_plan(draft.id, session)
    events = list_agent_draft_handoff_events_for_draft(session, draft.id)
    assert any(ev.step == "proof_plan" for ev in events)
