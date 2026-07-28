import json
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_agent_draft_bridge_event,
    create_automation_draft,
)
from erpguard.product.agent_draft_bridge_audit import get_bridge_audit


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
        opportunity_id="x", scan_id="x", snapshot_id="x", connection_id="x",
        name="Test", description="test", status="pending_review",
        runtime_mode="dry_run_only", write_actions=False,
        draft_json=json.dumps(draft_content),
    )


def test_audit_empty_no_events():
    session = _make_session()
    draft = _make_draft(session)
    result = get_bridge_audit(draft.id, session)
    assert result.draft_id == draft.id
    assert result.event_count == 0
    assert result.events == []


def test_audit_returns_events():
    session = _make_session()
    draft = _make_draft(session)
    create_agent_draft_bridge_event(session, draft.id, "prop1", "review", "passed", "{}")
    create_agent_draft_bridge_event(session, draft.id, "prop1", "validation", "failed", '{"issues": 1}')

    result = get_bridge_audit(draft.id, session)
    assert result.event_count == 2
    assert result.events[0].step == "review"
    assert result.events[1].step == "validation"


def test_audit_event_detail_parsed():
    session = _make_session()
    draft = _make_draft(session)
    create_agent_draft_bridge_event(
        session, draft.id, "prop1", "compile_plan", "passed",
        json.dumps({"plan_steps": 6})
    )
    result = get_bridge_audit(draft.id, session)
    assert result.events[0].detail == {"plan_steps": 6}


def test_audit_safety_constants():
    session = _make_session()
    draft = _make_draft(session)
    result = get_bridge_audit(draft.id, session)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_audit_for_nonexistent_draft():
    session = _make_session()
    result = get_bridge_audit("nonexistent_draft", session)
    assert result.event_count == 0
    assert result.events == []
