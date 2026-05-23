from __future__ import annotations

import pytest

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_advisory_session import AdvisorySessionService
from erpguard.product.agent_proposal_store import ProposalStore


def _make_session():
    init_db()
    return SessionLocal()


def test_generate_proposal_produces_non_executable_result():
    db = _make_session()
    try:
        session_svc = AdvisorySessionService(db)
        advisory = session_svc.create({"type": "test", "id": "t1"})
        session_id = advisory["session_id"]

        store = ProposalStore(db)
        proposal = store.generate(session_id, "List all draft sales orders daily at 8 AM")

        assert proposal["is_advisory_only"] is True
        assert proposal["can_execute"] is False
        assert proposal["proposal_id"].startswith("proposal_")
        assert proposal["session_id"] == session_id
        assert "workflow" in proposal
        assert "guards" in proposal
        assert "risk_summary" in proposal
        assert "clarification_questions" in proposal
    finally:
        db.close()


def test_generate_updates_session_status():
    db = _make_session()
    try:
        session_svc = AdvisorySessionService(db)
        advisory = session_svc.create({})
        session_id = advisory["session_id"]

        ProposalStore(db).generate(session_id, "Validate invoice formulas")

        updated_session = session_svc.get(session_id)
        assert updated_session["status"] == "proposal_generated"
        assert updated_session["latest_proposal_id"] is not None
    finally:
        db.close()


def test_get_proposal_returns_correct_data():
    db = _make_session()
    try:
        session_svc = AdvisorySessionService(db)
        advisory = session_svc.create({})
        store = ProposalStore(db)
        proposal = store.generate(advisory["session_id"], "Confirm sales orders with formula guard")
        retrieved = store.get(proposal["proposal_id"])

        assert retrieved["proposal_id"] == proposal["proposal_id"]
        assert retrieved["request_text"] == "Confirm sales orders with formula guard"
    finally:
        db.close()


def test_revise_increments_revision_number():
    db = _make_session()
    try:
        advisory = AdvisorySessionService(db).create({})
        store = ProposalStore(db)
        proposal = store.generate(advisory["session_id"], "Send invoice email")
        assert proposal["revision_number"] == 1

        revised = store.revise(proposal["proposal_id"], "Send invoice email daily to accountant")
        assert revised["revision_number"] == 2
        assert revised["status"] == "revised"
    finally:
        db.close()


def test_safety_summary_contains_invariants():
    db = _make_session()
    try:
        advisory = AdvisorySessionService(db).create({})
        store = ProposalStore(db)
        proposal = store.generate(advisory["session_id"], "Read partner data")
        safety = store.safety_summary(proposal["proposal_id"])

        assert safety["is_advisory_only"] is True
        assert safety["can_execute"] is False
        assert len(safety["safety_invariants"]) >= 4
        assert any("no ERP writes" in inv for inv in safety["safety_invariants"])
    finally:
        db.close()


def test_get_missing_proposal_raises():
    db = _make_session()
    try:
        with pytest.raises(ObjectNotFoundError):
            ProposalStore(db).get("proposal_doesnotexist")
    finally:
        db.close()


def test_generate_on_missing_session_raises():
    db = _make_session()
    try:
        with pytest.raises(ObjectNotFoundError):
            ProposalStore(db).generate("advisory_doesnotexist", "test request")
    finally:
        db.close()
