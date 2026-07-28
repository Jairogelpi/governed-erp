"""Sprint 36 — Agent Candidate Human Decision unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import AgentCandidateDecision, UISkillVersionRecord
from erpguard.product.agent_candidate_human_decision import record_human_decision


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    import erpguard.db.models  # noqa: F401
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()


def _make_version(db):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status="candidate",
        steps_json="[]",
        guard_names_json="[]",
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
    )
    db.add(rec)
    db.commit()
    return rec


def test_approve_decision(db):
    rec = _make_version(db)
    r = record_human_decision(rec.id, "approve", "human_reviewer", session=db)
    assert r.decision_id != ""
    assert r.decision == "approve"
    assert r.governance_status == "approved_pending_activation"


def test_reject_decision(db):
    rec = _make_version(db)
    r = record_human_decision(rec.id, "reject", "human_reviewer", rationale="Not safe", session=db)
    assert r.governance_status == "rejected"


def test_request_changes_decision(db):
    rec = _make_version(db)
    r = record_human_decision(rec.id, "request_changes", "reviewer", rationale="Needs fix", session=db)
    assert r.governance_status == "changes_requested"


def test_decision_persisted(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    row = db.query(AgentCandidateDecision).filter_by(version_id=rec.id).first()
    assert row is not None
    assert row.decision == "approve"


def test_safety_invariants(db):
    rec = _make_version(db)
    r = record_human_decision(rec.id, "approve", "reviewer", session=db)
    assert r.can_execute is False
    assert r.can_approve is False
    assert r.is_advisory_only is True


def test_invalid_decision_blocked(db):
    rec = _make_version(db)
    r = record_human_decision(rec.id, "activate", "reviewer", session=db)
    assert r.decision_id == ""
    assert r.blocking_reason != ""


def test_version_not_found(db):
    r = record_human_decision("nonexistent-id", "approve", "reviewer", session=db)
    assert r.blocking_reason == "version_not_found"


def test_multiple_decisions_allowed(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "request_changes", "r1", rationale="Fix X", session=db)
    record_human_decision(rec.id, "approve", "r2", session=db)
    count = db.query(AgentCandidateDecision).filter_by(version_id=rec.id).count()
    assert count == 2
