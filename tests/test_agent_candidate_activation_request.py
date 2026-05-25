"""Sprint 37 — Agent Candidate Activation Request unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_activation_gate_bridge import evaluate_activation_gate
from erpguard.product.agent_candidate_activation_request import create_activation_request
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


def _setup_eligible(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    return rec


def test_create_request_succeeds(db):
    rec = _setup_eligible(db)
    r = create_activation_request(rec.id, "operator", "ready for activation", session=db)
    assert r.eligible is True
    assert r.request_id != ""
    assert r.request_status == "pending_review"


def test_request_idempotent(db):
    rec = _setup_eligible(db)
    r1 = create_activation_request(rec.id, "operator", session=db)
    r2 = create_activation_request(rec.id, "operator2", session=db)
    assert r1.request_id == r2.request_id


def test_blocked_no_decision(db):
    rec = _make_version(db)
    r = create_activation_request(rec.id, "operator", session=db)
    assert r.eligible is False
    assert r.request_id == ""
    assert r.request_status == "blocked"


def test_blocked_no_gate(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = create_activation_request(rec.id, "operator", session=db)
    assert r.eligible is False
    assert "gate" in r.blocking_reason.lower()


def test_safety_invariants(db):
    rec = _setup_eligible(db)
    r = create_activation_request(rec.id, "operator", session=db)
    assert r.can_execute is False
    assert r.can_approve is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = create_activation_request("nonexistent-id", "operator", session=db)
    assert r.eligible is False
    assert r.blocking_reason == "version_not_found"


def test_request_does_not_change_version_status(db):
    rec = _setup_eligible(db)
    create_activation_request(rec.id, "operator", session=db)
    db.refresh(rec)
    assert rec.status == "candidate"
    assert rec.is_active is False


def test_requested_by_preserved(db):
    rec = _setup_eligible(db)
    r = create_activation_request(rec.id, "governance_operator", "approved by committee", session=db)
    assert r.requested_by == "governance_operator"
    assert r.rationale == "approved by committee"
