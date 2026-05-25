"""Sprint 36 — Agent Candidate Decision History unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_decision_history import get_decision_history
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


def test_empty_history(db):
    rec = _make_version(db)
    r = get_decision_history(rec.id, db)
    assert r.decision_count == 0
    assert r.latest_decision is None
    assert r.entries == []


def test_single_decision_in_history(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = get_decision_history(rec.id, db)
    assert r.decision_count == 1
    assert r.latest_decision == "approve"
    assert r.latest_governance_status == "approved_pending_activation"


def test_multiple_decisions_ordered(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "request_changes", "r1", rationale="Fix", session=db)
    record_human_decision(rec.id, "approve", "r2", session=db)
    r = get_decision_history(rec.id, db)
    assert r.decision_count == 2
    assert r.latest_decision == "approve"
    assert r.entries[0].decision == "request_changes"
    assert r.entries[1].decision == "approve"


def test_history_entry_fields(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "reject", "operator", rationale="Too risky", session=db)
    r = get_decision_history(rec.id, db)
    entry = r.entries[0]
    assert entry.decision == "reject"
    assert entry.actor == "operator"
    assert entry.rationale == "Too risky"
    assert entry.governance_status == "rejected"
    assert entry.created_at is not None


def test_version_not_found(db):
    r = get_decision_history("nonexistent-id", db)
    assert r.decision_count == 0
    assert r.latest_decision is None


def test_safety_flags(db):
    rec = _make_version(db)
    r = get_decision_history(rec.id, db)
    assert r.can_execute is False
    assert r.is_advisory_only is True
