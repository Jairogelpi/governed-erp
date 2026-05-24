import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_agent_draft_handoff_event,
    create_automation_draft,
)
from erpguard.product.agent_draft_handoff_audit import get_handoff_audit


def _make_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _make_draft(session):
    return create_automation_draft(
        session,
        opportunity_id="x", scan_id="x", snapshot_id="x", connection_id="x",
        name="Test", description="test", status="pending_review",
        runtime_mode="dry_run_only", write_actions=False,
        draft_json=json.dumps({"source": "agent_advisory_proposal", "safety": {"can_execute": False}}),
    )


def test_audit_empty():
    session = _make_session()
    draft = _make_draft(session)
    result = get_handoff_audit(draft.id, session)
    assert result.event_count == 0
    assert result.events == []


def test_audit_returns_events():
    session = _make_session()
    draft = _make_draft(session)
    create_agent_draft_handoff_event(session, draft.id, "p1", "proof_plan", "passed", "{}")
    create_agent_draft_handoff_event(session, draft.id, "p1", "evidence", "assembled", "{}")
    create_agent_draft_handoff_event(session, draft.id, "p1", "handoff_packet", "created", "{}")

    result = get_handoff_audit(draft.id, session)
    assert result.event_count == 3
    steps = [e.step for e in result.events]
    assert "proof_plan" in steps
    assert "evidence" in steps
    assert "handoff_packet" in steps


def test_audit_detail_parsed():
    session = _make_session()
    draft = _make_draft(session)
    create_agent_draft_handoff_event(
        session, draft.id, "p1", "proof_plan", "passed",
        json.dumps({"scenarios": 5})
    )
    result = get_handoff_audit(draft.id, session)
    assert result.events[0].detail == {"scenarios": 5}


def test_audit_safety_constants():
    session = _make_session()
    draft = _make_draft(session)
    result = get_handoff_audit(draft.id, session)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_audit_nonexistent_draft():
    session = _make_session()
    result = get_handoff_audit("nonexistent", session)
    assert result.event_count == 0
