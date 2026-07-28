import json
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
from erpguard.product.agent_draft_approval_handoff import create_approval_handoff_packet


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_full_setup(session):
    adv = create_advisory_session(session, created_by_actor_json="{}")
    proposal = create_advisory_proposal(
        session,
        session_id=adv.id,
        request_text="Generate daily sales report",
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
        "safety": {
            "runtime_mode": "dry_run_only",
            "write_actions": False,
            "can_execute": False,
            "is_advisory_only": True,
            "requires_human_review": True,
            "requires_approval": True,
        },
    }
    draft = create_automation_draft(
        session,
        opportunity_id="agent_advisory",
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
    create_agent_proposal_draft_link(session, proposal_id=proposal.id, draft_id=draft.id, session_id=adv.id)
    return draft, proposal, adv


def test_handoff_packet_created():
    session = _make_session()
    draft, proposal, _ = _make_full_setup(session)
    result = create_approval_handoff_packet(draft.id, session)
    assert result.packet_id != ""
    assert result.draft_id == draft.id
    assert result.proposal_id == proposal.id


def test_handoff_packet_has_sections():
    session = _make_session()
    draft, _, _ = _make_full_setup(session)
    result = create_approval_handoff_packet(draft.id, session)
    section_ids = {s.section_id for s in result.sections}
    assert "sec_proposal" in section_ids
    assert "sec_draft" in section_ids
    assert "sec_safety" in section_ids
    assert "sec_readiness" in section_ids
    assert "sec_instructions" in section_ids


def test_handoff_packet_safety_constants():
    session = _make_session()
    draft, _, _ = _make_full_setup(session)
    result = create_approval_handoff_packet(draft.id, session)
    assert result.can_approve is False
    assert result.can_execute is False
    assert result.is_advisory_only is True
    assert result.status == "pending_human_review"


def test_handoff_packet_approval_instructions():
    session = _make_session()
    draft, _, _ = _make_full_setup(session)
    result = create_approval_handoff_packet(draft.id, session)
    assert "human" in result.approval_instructions.lower()
    assert "does not automatically activate" in result.approval_instructions.lower()


def test_handoff_packet_idempotent():
    session = _make_session()
    draft, _, _ = _make_full_setup(session)
    r1 = create_approval_handoff_packet(draft.id, session)
    r2 = create_approval_handoff_packet(draft.id, session)
    assert r1.packet_id == r2.packet_id
    assert r2.is_cached is True


def test_handoff_draft_not_found():
    session = _make_session()
    result = create_approval_handoff_packet("nonexistent", session)
    assert result.status == "blocked"
    assert "not found" in result.approval_instructions.lower()


def test_handoff_packet_includes_bridge_results():
    session = _make_session()
    draft, proposal, _ = _make_full_setup(session)
    for step in ("review", "validation", "compile_plan"):
        create_agent_draft_bridge_event(session, draft.id, proposal.id, step, "passed", "{}")
    create_agent_draft_handoff_event(session, draft.id, proposal.id, "proof_plan", "passed", "{}")

    result = create_approval_handoff_packet(draft.id, session)
    bridge_section = next((s for s in result.sections if s.section_id == "sec_bridge"), None)
    assert bridge_section is not None
    assert "review" in bridge_section.content


def test_handoff_readiness_score_in_result():
    session = _make_session()
    draft, proposal, _ = _make_full_setup(session)
    for step in ("review", "validation", "compile_plan"):
        create_agent_draft_bridge_event(session, draft.id, proposal.id, step, "passed", "{}")
    create_agent_draft_handoff_event(session, draft.id, proposal.id, "proof_plan", "passed", "{}")

    result = create_approval_handoff_packet(draft.id, session)
    assert result.readiness_score == 100
    assert result.ready_for_review is True
