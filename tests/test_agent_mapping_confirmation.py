from __future__ import annotations

import json
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.db.repositories import (
    create_advisory_proposal,
    create_advisory_session,
    list_mapping_confirmations_for_proposal,
)
from erpguard.product.agent_mapping_confirmation import (
    confirm_mapping,
    list_mapping_confirmations,
    reject_mapping,
)


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
    mappings = [
        {"field": "state", "odoo_field": "state", "odoo_model": "sale.order", "required": True},
        {"field": "partner_id", "odoo_field": "partner_id", "odoo_model": "sale.order", "required": True},
    ]
    return create_advisory_proposal(
        session,
        session_id=sess.id,
        request_text="test",
        intent_json="{}",
        process_category="sales_cycle",
        entity_mappings_json=json.dumps(mappings),
        workflow_json="{}",
        guards_json="{}",
        risk_summary_json="{}",
        clarification_questions_json="[]",
        revision_number=1,
        status="draft",
    )


def test_confirm_mapping(session):
    proposal = _make_proposal(session)
    result = confirm_mapping(proposal.id, "state", "Correct field", session)
    assert result.action == "confirmed"
    assert result.mapping_key == "state"
    assert result.reason == "Correct field"


def test_reject_mapping(session):
    proposal = _make_proposal(session)
    result = reject_mapping(proposal.id, "partner_id", "Wrong model", session)
    assert result.action == "rejected"
    assert result.mapping_key == "partner_id"


def test_previous_action_tracked(session):
    proposal = _make_proposal(session)
    confirm_mapping(proposal.id, "state", None, session)
    result = reject_mapping(proposal.id, "state", "Changed mind", session)
    assert result.previous_action == "confirmed"


def test_confirmations_persisted(session):
    proposal = _make_proposal(session)
    confirm_mapping(proposal.id, "state", None, session)
    reject_mapping(proposal.id, "partner_id", None, session)
    rows = list_mapping_confirmations_for_proposal(session, proposal.id)
    assert len(rows) == 2


def test_list_mapping_confirmations_deduplicates_by_latest(session):
    proposal = _make_proposal(session)
    confirm_mapping(proposal.id, "state", None, session)
    reject_mapping(proposal.id, "state", "Changed", session)
    view = list_mapping_confirmations(proposal.id, session)
    state_entry = next(c for c in view.confirmations if c.mapping_key == "state")
    assert state_entry.action == "rejected"


def test_confirmation_is_advisory_only(session):
    proposal = _make_proposal(session)
    result = confirm_mapping(proposal.id, "state", None, session)
    assert result.is_advisory_only is True
    assert result.can_execute is False


def test_audit_event_on_confirm(session):
    from erpguard.db.repositories import list_clarification_audit_events_for_proposal
    proposal = _make_proposal(session)
    confirm_mapping(proposal.id, "state", None, session)
    events = list_clarification_audit_events_for_proposal(session, proposal.id)
    assert any(e.event_type == "mapping_confirmed" for e in events)
