from __future__ import annotations

import pytest

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_advisory_session import AdvisorySessionService
from erpguard.product.agent_draft_service import AgentDraftService
from erpguard.product.agent_proposal_store import ProposalStore


def _db():
    init_db()
    return SessionLocal()


def _create_eligible_proposal(db):
    session_svc = AdvisorySessionService(db)
    advisory = session_svc.create({"type": "test"})
    store = ProposalStore(db)
    proposal = store.generate(
        advisory["session_id"],
        "List all draft sales orders and send a daily report",
    )
    return proposal


def test_preview_returns_draft_preview():
    db = _db()
    try:
        proposal = _create_eligible_proposal(db)
        svc = AgentDraftService(db)
        preview = svc.preview(proposal["proposal_id"])
        assert preview.proposal_id == proposal["proposal_id"]
        assert preview.draft_runtime_mode == "dry_run_only"
        assert preview.draft_write_actions is False
    finally:
        db.close()


def test_create_draft_produces_automation_draft():
    db = _db()
    try:
        proposal = _create_eligible_proposal(db)
        svc = AgentDraftService(db)
        result = svc.create_draft(proposal["proposal_id"])
        assert result["draft_id"].startswith("automation_draft_")
        assert result["proposal_id"] == proposal["proposal_id"]
        assert result["runtime_mode"] == "dry_run_only"
        assert result["write_actions"] is False
        assert result["safety"]["can_execute"] is False
        assert result["safety"]["is_advisory_only"] is True
        assert result["next_step"] == "human_review"
    finally:
        db.close()


def test_create_draft_twice_raises():
    db = _db()
    try:
        proposal = _create_eligible_proposal(db)
        svc = AgentDraftService(db)
        svc.create_draft(proposal["proposal_id"])
        with pytest.raises(ValueError, match="draft already exists"):
            svc.create_draft(proposal["proposal_id"])
    finally:
        db.close()


def test_get_draft_link_after_create():
    db = _db()
    try:
        proposal = _create_eligible_proposal(db)
        svc = AgentDraftService(db)
        draft = svc.create_draft(proposal["proposal_id"])

        link = svc.get_draft_link(proposal["proposal_id"])
        assert link["has_draft"] is True
        assert link["draft_id"] == draft["draft_id"]
    finally:
        db.close()


def test_get_draft_link_before_create_returns_no_draft():
    db = _db()
    try:
        proposal = _create_eligible_proposal(db)
        svc = AgentDraftService(db)
        link = svc.get_draft_link(proposal["proposal_id"])
        assert link["has_draft"] is False
        assert link["draft_id"] is None
    finally:
        db.close()


def test_get_source_proposal_reverse_lookup():
    db = _db()
    try:
        proposal = _create_eligible_proposal(db)
        svc = AgentDraftService(db)
        draft = svc.create_draft(proposal["proposal_id"])

        source = svc.get_source_proposal(draft["draft_id"])
        assert source["proposal_id"] == proposal["proposal_id"]
        assert source["draft_id"] == draft["draft_id"]
        assert "proposal" in source
    finally:
        db.close()


def test_preview_missing_proposal_raises():
    db = _db()
    try:
        with pytest.raises(ObjectNotFoundError):
            AgentDraftService(db).preview("proposal_ghost")
    finally:
        db.close()


def test_create_draft_missing_proposal_raises():
    db = _db()
    try:
        with pytest.raises(ObjectNotFoundError):
            AgentDraftService(db).create_draft("proposal_ghost")
    finally:
        db.close()
