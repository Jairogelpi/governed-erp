"""Sprint 40 — Operator Next Step Recommender unit tests."""
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
from erpguard.product.operator_next_step_recommender import recommend_next_steps


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


def _full_activate(db, rec):
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    create_activation_request(rec.id, "operator", session=db)
    evaluate_final_activation_gate(rec.id, db)
    activate_candidate_version(rec.id, "operator", session=db)


def test_next_steps_present_for_fresh_candidate(db):
    rec = _make_version(db)
    r = recommend_next_steps(rec.id, db)
    assert r.step_count > 0
    assert r.all_steps_complete is False


def test_next_steps_safety_invariants(db):
    rec = _make_version(db)
    r = recommend_next_steps(rec.id, db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_governance_status_active_after_activation(db):
    rec = _make_version(db)
    _full_activate(db, rec)
    r = recommend_next_steps(rec.id, db)
    assert r.governance_status == "active_governed"


def test_all_steps_complete_after_full_flow(db):
    rec = _make_version(db)
    _full_activate(db, rec)
    get_run_preview(rec.id, db)
    r = recommend_next_steps(rec.id, db)
    assert r.all_steps_complete is True
    assert r.next_steps[0].action == "governance_complete"


def test_step_count_decreases_as_governance_progresses(db):
    rec = _make_version(db)
    before = recommend_next_steps(rec.id, db).step_count
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    after = recommend_next_steps(rec.id, db).step_count
    assert after < before


def test_version_not_found(db):
    r = recommend_next_steps("nonexistent-id", db)
    assert r.blocking_reason == "version_not_found"
    assert r.step_count == 0


def test_step_fields_populated(db):
    rec = _make_version(db)
    r = recommend_next_steps(rec.id, db)
    step = r.next_steps[0]
    assert step.step_number >= 1
    assert step.action != ""
    assert step.rationale != ""
    assert step.severity in ("blocking", "warning", "info", "complete")
