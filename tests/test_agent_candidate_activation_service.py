"""Sprint 38 — Agent Candidate Activation Service unit tests."""
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
from erpguard.product.agent_candidate_activation_service import activate_candidate_version
from erpguard.product.agent_candidate_final_activation_gate import evaluate_final_activation_gate
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


def _make_version(db, *, skill_id=None, status="candidate"):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    sid = skill_id or f"skill_{uuid.uuid4().hex[:8]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=sid,
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status=status,
        steps_json="[]",
        guard_names_json="[]",
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
    )
    db.add(rec)
    db.commit()
    return rec


def _full_prereqs(db, rec=None):
    if rec is None:
        rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    create_activation_request(rec.id, "operator", session=db)
    evaluate_final_activation_gate(rec.id, db)
    return rec


def test_activate_succeeds(db):
    rec = _full_prereqs(db)
    r = activate_candidate_version(rec.id, "operator", session=db)
    assert r.activated is True
    assert r.version_status == "active"
    assert r.is_active is True


def test_version_record_updated(db):
    rec = _full_prereqs(db)
    activate_candidate_version(rec.id, "operator", session=db)
    db.refresh(rec)
    assert rec.status == "active"
    assert rec.is_active is True


def test_no_execution_on_activation(db):
    rec = _full_prereqs(db)
    r = activate_candidate_version(rec.id, "operator", session=db)
    assert r.is_executed is False
    assert r.can_execute is False


def test_prior_version_deactivated(db):
    """Activating a new version should deactivate the previous active one."""
    shared_skill = f"skill_{uuid.uuid4().hex[:8]}"
    prior = _make_version(db, skill_id=shared_skill)
    _full_prereqs(db, prior)
    activate_candidate_version(prior.id, "operator", session=db)
    db.refresh(prior)
    assert prior.is_active is True

    new_ver = _make_version(db, skill_id=shared_skill)
    _full_prereqs(db, new_ver)
    r = activate_candidate_version(new_ver.id, "operator", session=db)

    db.refresh(prior)
    db.refresh(new_ver)
    assert new_ver.is_active is True
    assert prior.is_active is False
    assert r.prior_version_deactivated is True
    assert r.prior_version_id == prior.id


def test_idempotent_already_active(db):
    rec = _full_prereqs(db)
    r1 = activate_candidate_version(rec.id, "operator", session=db)
    r2 = activate_candidate_version(rec.id, "operator", session=db)
    assert r1.activated is True
    assert r2.activated is True
    db.refresh(rec)
    assert rec.status == "active"


def test_blocked_no_decision(db):
    rec = _make_version(db)
    r = activate_candidate_version(rec.id, "operator", session=db)
    assert r.activated is False
    assert r.blocking_reason != ""


def test_safety_invariants(db):
    rec = _full_prereqs(db)
    r = activate_candidate_version(rec.id, "operator", session=db)
    assert r.can_execute is False
    assert r.can_approve is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = activate_candidate_version("nonexistent-id", "operator", session=db)
    assert r.activated is False
    assert r.blocking_reason == "version_not_found"


def test_blocked_missing_final_gate(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    create_activation_request(rec.id, "operator", session=db)
    # No final gate evaluation
    r = activate_candidate_version(rec.id, "operator", session=db)
    assert r.activated is False
    assert "final" in r.blocking_reason.lower() or "gate" in r.blocking_reason.lower()
