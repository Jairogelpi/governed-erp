from __future__ import annotations

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
    create_clarification_answer,
    create_mapping_confirmation,
    get_automation_draft,
)
from erpguard.product.agent_draft_metadata_refresh import refresh_draft_metadata


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _setup(session):
    adv_session = create_advisory_session(session, created_by_actor_json="{}")
    proposal = create_advisory_proposal(
        session,
        session_id=adv_session.id,
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
    draft = create_automation_draft(
        session,
        opportunity_id=f"agent_proposal:{proposal.id}",
        scan_id="agent_advisory",
        snapshot_id="agent_advisory",
        connection_id="agent_advisory",
        name="Test draft",
        description="desc",
        runtime_mode="dry_run_only",
        write_actions=False,
        draft_json=json.dumps({"runtime_mode": "dry_run_only", "write_actions": False, "can_execute": False}),
        status="pending_review",
    )
    create_agent_proposal_draft_link(session, proposal.id, draft.id, adv_session.id)
    return proposal, draft


def test_refresh_updates_draft_json(session):
    proposal, draft = _setup(session)
    create_clarification_answer(session, proposal.id, "q1", "scheduled")
    create_mapping_confirmation(session, proposal.id, "state", "confirmed")
    result = refresh_draft_metadata(draft.id, session)
    assert result.refreshed is True
    assert result.answers_applied == 1
    assert result.confirmations_applied == 1


def test_refresh_draft_json_contains_metadata(session):
    proposal, draft = _setup(session)
    refresh_draft_metadata(draft.id, session)
    refreshed_draft = get_automation_draft(session, draft.id)
    dj = json.loads(refreshed_draft.draft_json)
    assert "clarification_metadata" in dj


def test_refresh_keeps_dry_run_mode(session):
    proposal, draft = _setup(session)
    refresh_draft_metadata(draft.id, session)
    refreshed_draft = get_automation_draft(session, draft.id)
    dj = json.loads(refreshed_draft.draft_json)
    assert dj["runtime_mode"] == "dry_run_only"
    assert dj["write_actions"] is False
    assert dj["can_execute"] is False


def test_refresh_unknown_draft(session):
    result = refresh_draft_metadata("automation_draft_missing", session)
    assert result.refreshed is False
    assert result.blocking_reason == "draft_not_found"


def test_refresh_draft_no_link(session):
    create_advisory_session(session, created_by_actor_json="{}")
    draft = create_automation_draft(
        session,
        opportunity_id="other",
        scan_id="other",
        snapshot_id="other",
        connection_id="other",
        name="orphan draft",
        description="",
        runtime_mode="dry_run_only",
        write_actions=False,
        draft_json="{}",
        status="pending_review",
    )
    result = refresh_draft_metadata(draft.id, session)
    assert result.refreshed is False
    assert result.blocking_reason == "no_proposal_link"


def test_refresh_result_is_advisory_only(session):
    _, draft = _setup(session)
    result = refresh_draft_metadata(draft.id, session)
    assert result.is_advisory_only is True
    assert result.can_execute is False
    assert result.runtime_mode == "dry_run_only"


def test_refresh_audit_event_created(session):
    from erpguard.db.repositories import list_clarification_audit_events_for_proposal
    proposal, draft = _setup(session)
    refresh_draft_metadata(draft.id, session)
    events = list_clarification_audit_events_for_proposal(session, proposal.id)
    assert any(e.event_type == "draft_metadata_refreshed" for e in events)
