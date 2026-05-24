from __future__ import annotations

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    create_clarification_audit_event,
)
from erpguard.product.agent_clarification_audit import get_clarification_audit


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _make_proposal(session):
    sess = create_advisory_session(session, created_by_actor_json="{}")
    return create_advisory_proposal(
        session,
        session_id=sess.id,
        request_text="test",
        intent_json="{}",
        process_category="sales_cycle",
        entity_mappings_json="[]",
        workflow_json="{}",
        guards_json="{}",
        risk_summary_json="{}",
        clarification_questions_json="[]",
        revision_number=1,
        status="draft",
    )


def test_empty_audit(session):
    proposal = _make_proposal(session)
    audit = get_clarification_audit(proposal.id, session)
    assert audit.event_count == 0
    assert audit.events == []


def test_audit_returns_events(session):
    proposal = _make_proposal(session)
    create_clarification_audit_event(session, proposal.id, "answers_submitted", json.dumps({"submitted": ["q1"]}))
    create_clarification_audit_event(session, proposal.id, "mapping_confirmed", json.dumps({"mapping_key": "state"}))
    audit = get_clarification_audit(proposal.id, session)
    assert audit.event_count == 2


def test_audit_event_types(session):
    proposal = _make_proposal(session)
    create_clarification_audit_event(session, proposal.id, "mapping_rejected", "{}")
    audit = get_clarification_audit(proposal.id, session)
    types = [e.event_type for e in audit.events]
    assert "mapping_rejected" in types


def test_audit_detail_parsed(session):
    proposal = _make_proposal(session)
    create_clarification_audit_event(
        session, proposal.id, "draft_metadata_refreshed",
        json.dumps({"draft_id": "automation_draft_x", "answers_applied": 2})
    )
    audit = get_clarification_audit(proposal.id, session)
    entry = audit.events[0]
    assert entry.detail["answers_applied"] == 2


def test_audit_is_advisory_only(session):
    proposal = _make_proposal(session)
    audit = get_clarification_audit(proposal.id, session)
    assert audit.is_advisory_only is True
    assert audit.can_execute is False
