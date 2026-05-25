"""Sprint 39 — Agent Skill Run Plan Builder unit tests."""
from __future__ import annotations

import json
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
from erpguard.product.agent_skill_run_plan_builder import build_run_plan


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


def _make_version(db, *, steps_json="[]", guard_names_json="[]"):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status="candidate",
        steps_json=steps_json,
        guard_names_json=guard_names_json,
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


def test_plan_built_empty_steps(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = build_run_plan(rec.id, db)
    assert r.plan_ready is True
    assert r.step_count == 1  # advisory placeholder step
    assert r.steps[0].step_type == "advisory_read"


def test_plan_built_with_steps(db):
    steps = json.dumps([
        {"id": "s1", "type": "read", "description": "Read order"},
        {"id": "s2", "type": "validate", "description": "Validate formula"},
    ])
    rec = _make_version(db, steps_json=steps)
    _activate(db, rec)
    r = build_run_plan(rec.id, db)
    assert r.plan_ready is True
    assert r.step_count == 2
    assert r.steps[0].step_id == "s1"
    assert r.steps[1].step_id == "s2"


def test_plan_never_executes(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = build_run_plan(rec.id, db)
    assert r.will_execute is False
    assert r.plan_is_dry_run is True
    for step in r.steps:
        assert step.will_execute is False


def test_plan_blocked_not_active(db):
    rec = _make_version(db)
    r = build_run_plan(rec.id, db)
    assert r.plan_ready is False
    assert r.blocking_reason != ""


def test_guard_names_included(db):
    rec = _make_version(db, guard_names_json='["formula_guard"]')
    _activate(db, rec)
    r = build_run_plan(rec.id, db)
    assert "formula_guard" in r.guard_names


def test_safety_invariants(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = build_run_plan(rec.id, db)
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = build_run_plan("nonexistent-id", db)
    assert r.plan_ready is False
    assert r.blocking_reason == "version_not_found"
