"""Sprint 39 — Agent Skill Run Preview Audit unit tests."""
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
from erpguard.product.agent_skill_run_preview import get_run_preview
from erpguard.product.agent_skill_run_preview_audit import get_run_preview_audit


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


def _activate(db, rec):
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    create_activation_request(rec.id, "operator", session=db)
    evaluate_final_activation_gate(rec.id, db)
    activate_candidate_version(rec.id, "operator", session=db)


def test_audit_empty_before_any_preview(db):
    rec = _make_version(db)
    _activate(db, rec)
    result = get_run_preview_audit(rec.id, db)
    assert result.events == []
    assert result.version_id == rec.id


def test_audit_after_execution_gate(db):
    rec = _make_version(db)
    _activate(db, rec)
    evaluate_execution_gate(rec.id, db)
    result = get_run_preview_audit(rec.id, db)
    steps = [e.step for e in result.events]
    assert "execution_gate_evaluated" in steps


def test_audit_after_full_preview(db):
    rec = _make_version(db)
    _activate(db, rec)
    get_run_preview(rec.id, db)
    result = get_run_preview_audit(rec.id, db)
    steps = [e.step for e in result.events]
    assert "execution_gate_evaluated" in steps
    assert "run_preview_completed" in steps


def test_audit_event_fields(db):
    rec = _make_version(db)
    _activate(db, rec)
    evaluate_execution_gate(rec.id, db)
    result = get_run_preview_audit(rec.id, db)
    assert len(result.events) >= 1
    event = result.events[0]
    assert event.version_id == rec.id
    assert event.step != ""
    assert event.status != ""
    assert event.created_at is not None


def test_audit_safety_invariants(db):
    rec = _make_version(db)
    _activate(db, rec)
    get_run_preview(rec.id, db)
    result = get_run_preview_audit(rec.id, db)
    assert result.will_execute is False
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_audit_version_not_found(db):
    result = get_run_preview_audit("nonexistent-id", db)
    assert result.events == []
    assert result.version_id == "nonexistent-id"


def test_audit_accumulates_multiple_calls(db):
    rec = _make_version(db)
    _activate(db, rec)
    get_run_preview(rec.id, db)
    get_run_preview(rec.id, db)
    result = get_run_preview_audit(rec.id, db)
    steps = [e.step for e in result.events]
    assert steps.count("run_preview_completed") >= 2
