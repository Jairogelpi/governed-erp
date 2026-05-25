"""Sprint 39 — Agent Skill Execution Gate unit tests."""
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
from erpguard.product.agent_skill_execution_gate import evaluate_execution_gate


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


def _make_version(db, *, runtime_type="agent_advisory"):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status="candidate",
        steps_json="[]",
        guard_names_json="[]",
        runtime_type=runtime_type,
        promotion_readiness_json="{}",
    )
    db.add(rec)
    db.commit()
    return rec


def _activate(db, rec):
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    create_activation_request(rec.id, "operator", session=db)
    evaluate_final_activation_gate(rec.id, db)
    activate_candidate_version(rec.id, "operator", session=db)


def test_gate_passes_active_version(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = evaluate_execution_gate(rec.id, db)
    assert r.gate_passed is True
    assert r.execution_ready is True


def test_will_execute_always_false(db):
    """execution_ready=True means the version COULD be run — it does not run."""
    rec = _make_version(db)
    _activate(db, rec)
    r = evaluate_execution_gate(rec.id, db)
    assert r.will_execute is False
    assert r.can_execute is False


def test_gate_fails_not_active(db):
    rec = _make_version(db)
    r = evaluate_execution_gate(rec.id, db)
    assert r.gate_passed is False
    assert r.execution_ready is False


def test_gate_fails_no_decision(db):
    rec = _make_version(db)
    r = evaluate_execution_gate(rec.id, db)
    assert r.gate_passed is False


def test_checks_populated(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = evaluate_execution_gate(rec.id, db)
    check_names = [c.check for c in r.checks]
    assert "version_is_active" in check_names
    assert "approved_decision_on_record" in check_names
    assert "activation_request_on_record" in check_names
    assert "runtime_type_safe" in check_names
    assert "no_real_erp_writes" in check_names
    assert "preview_does_not_execute" in check_names


def test_safety_invariants(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = evaluate_execution_gate(rec.id, db)
    assert r.is_advisory_only is True
    assert r.can_execute is False


def test_version_not_found(db):
    r = evaluate_execution_gate("nonexistent-id", db)
    assert r.gate_passed is False
    assert r.blocking_reason == "version_not_found"


def test_gate_emits_audit_event(db):
    from erpguard.db.repositories import list_agent_skill_run_preview_events_for_version
    rec = _make_version(db)
    _activate(db, rec)
    evaluate_execution_gate(rec.id, db)
    events = list_agent_skill_run_preview_events_for_version(db, rec.id)
    steps = [e.step for e in events]
    assert "execution_gate_evaluated" in steps
