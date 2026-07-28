"""Sprint 36 — Agent Candidate Activation Gate Bridge unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_activation_gate_bridge import evaluate_activation_gate
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


def _make_version(db, *, status="candidate", runtime_type="agent_advisory"):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status=status,
        steps_json="[]",
        guard_names_json="[]",
        runtime_type=runtime_type,
        promotion_readiness_json="{}",
    )
    db.add(rec)
    db.commit()
    return rec


def test_gate_passes_with_approve(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = evaluate_activation_gate(rec.id, db)
    assert r.gate_passed is True
    assert r.latest_decision == "approve"


def test_gate_never_activates(db):
    """activation_allowed must always be False — gate evaluates only."""
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = evaluate_activation_gate(rec.id, db)
    assert r.activation_allowed is False


def test_gate_fails_no_decision(db):
    rec = _make_version(db)
    r = evaluate_activation_gate(rec.id, db)
    assert r.gate_passed is False
    assert any("decision" in b.lower() for b in r.blocking_reasons)


def test_gate_fails_rejected_decision(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "reject", "reviewer", session=db)
    r = evaluate_activation_gate(rec.id, db)
    assert r.gate_passed is False


def test_gate_fails_wrong_status(db):
    rec = _make_version(db, status="draft")
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = evaluate_activation_gate(rec.id, db)
    assert r.gate_passed is False
    assert any("candidate" in b for b in r.blocking_reasons)


def test_checks_populated(db):
    rec = _make_version(db)
    r = evaluate_activation_gate(rec.id, db)
    check_names = [c.check for c in r.checks]
    assert "version_is_candidate" in check_names
    assert "human_decision_exists" in check_names
    assert "latest_decision_is_approve" in check_names


def test_safety_invariants(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = evaluate_activation_gate(rec.id, db)
    assert r.can_execute is False
    assert r.can_approve is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = evaluate_activation_gate("nonexistent-id", db)
    assert r.gate_passed is False
    assert r.blocking_reason == "version_not_found"


def test_candidate_status_unchanged_after_gate(db):
    """Gate evaluation must not change the version status."""
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    db.refresh(rec)
    assert rec.status == "candidate"
    assert rec.is_active is False
