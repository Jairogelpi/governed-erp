import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    create_agent_proposal_draft_link,
    create_agent_draft_bridge_event,
    create_agent_draft_handoff_event,
    create_automation_draft,
)
from erpguard.product.agent_draft_approval_readiness import check_approval_readiness


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_full_setup(session):
    adv = create_advisory_session(session, created_by_actor_json="{}")
    proposal = create_advisory_proposal(
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
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)
    return draft, proposal


def test_readiness_draft_not_found():
    session = _make_session()
    result = check_approval_readiness("nonexistent", session)
    assert result.ready is False
    assert result.overall_score == 0


def test_readiness_no_bridge_steps():
    session = _make_session()
    draft, _ = _make_full_setup(session)
    result = check_approval_readiness(draft.id, session)
    assert result.ready is False
    assert any("bridge" in b.lower() for b in result.blocking_items)


def test_readiness_with_all_bridge_steps():
    session = _make_session()
    draft, proposal = _make_full_setup(session)
    for step in ("review", "validation", "compile_plan"):
        create_agent_draft_bridge_event(session, draft.id, proposal.id, step, "passed", "{}")
    create_agent_draft_handoff_event(session, draft.id, proposal.id, "proof_plan", "passed", "{}")

    result = check_approval_readiness(draft.id, session)
    assert result.ready is True
    assert result.overall_score == 100


def test_readiness_safety_constants():
    session = _make_session()
    draft, _ = _make_full_setup(session)
    result = check_approval_readiness(draft.id, session)
    assert result.can_approve is False
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_readiness_checklist_has_required_items():
    session = _make_session()
    draft, _ = _make_full_setup(session)
    result = check_approval_readiness(draft.id, session)
    check_ids = {c.check_id for c in result.checklist}
    assert "chk_eligibility" in check_ids
    assert "chk_dry_run_only" in check_ids
    assert "chk_write_actions_false" in check_ids


def test_readiness_score_improves_with_steps():
    session = _make_session()
    draft, proposal = _make_full_setup(session)

    result_before = check_approval_readiness(draft.id, session)
    score_before = result_before.overall_score

    for step in ("review", "validation", "compile_plan"):
        create_agent_draft_bridge_event(session, draft.id, proposal.id, step, "passed", "{}")
    create_agent_draft_handoff_event(session, draft.id, proposal.id, "proof_plan", "passed", "{}")

    result_after = check_approval_readiness(draft.id, session)
    assert result_after.overall_score > score_before


def test_readiness_ineligible_draft():
    session = _make_session()
    bad_content = {"source": "manual", "safety": {"can_execute": False}}
    draft = create_automation_draft(
        session,
        opportunity_id="x", scan_id="x", snapshot_id="x", connection_id="x",
        name="bad", description="bad", status="pending_review",
        runtime_mode="dry_run_only", write_actions=False,
        draft_json=json.dumps(bad_content),
    )
    result = check_approval_readiness(draft.id, session)
    assert result.ready is False
    assert any("eligible" in b.lower() for b in result.blocking_items)


def test_readiness_partial_blocks():
    session = _make_session()
    draft, proposal = _make_full_setup(session)
    create_agent_draft_bridge_event(session, draft.id, proposal.id, "review", "passed", "{}")

    result = check_approval_readiness(draft.id, session)
    assert result.ready is False
    assert len(result.blocking_items) > 0
