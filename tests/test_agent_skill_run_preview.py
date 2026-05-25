"""Sprint 39 — Agent Skill Run Preview orchestration unit tests."""
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
from erpguard.product.agent_skill_run_preview import get_run_preview


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


def test_preview_ready_after_full_flow(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = get_run_preview(rec.id, db)
    assert r.preview_ready is True
    assert r.eligible is True
    assert r.plan_ready is True
    assert r.gate_passed is True
    assert r.execution_ready is True


def test_preview_never_executes(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = get_run_preview(rec.id, db)
    assert r.will_execute is False
    assert r.can_execute is False


def test_preview_not_ready_without_activation(db):
    rec = _make_version(db)
    r = get_run_preview(rec.id, db)
    assert r.preview_ready is False
    assert r.eligible is False


def test_preview_emits_event(db):
    from erpguard.db.repositories import list_agent_skill_run_preview_events_for_version
    rec = _make_version(db)
    _activate(db, rec)
    get_run_preview(rec.id, db)
    events = list_agent_skill_run_preview_events_for_version(db, rec.id)
    steps = [e.step for e in events]
    assert "run_preview_completed" in steps


def test_safety_invariants(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = get_run_preview(rec.id, db)
    assert r.is_advisory_only is True
    assert r.can_execute is False


def test_version_not_found(db):
    r = get_run_preview("nonexistent-id", db)
    assert r.preview_ready is False
    assert r.blocking_reason == "version_not_found"
