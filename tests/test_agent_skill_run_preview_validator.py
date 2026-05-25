"""Sprint 39 — Agent Skill Run Preview Validator unit tests."""
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
from erpguard.product.agent_skill_run_preview_validator import validate_run_preview_eligibility


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


def _make_version(db, *, runtime_type="agent_advisory", llm_required=False):
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
        llm_required=llm_required,
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


def test_eligible_active_version(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = validate_run_preview_eligibility(rec.id, db)
    assert r.eligible is True
    assert r.blocking_reasons == []


def test_not_eligible_candidate_status(db):
    rec = _make_version(db)
    r = validate_run_preview_eligibility(rec.id, db)
    assert r.eligible is False
    assert any("active" in b.lower() for b in r.blocking_reasons)


def test_not_eligible_no_activation_request(db):
    """Active version that bypassed governance flow — no activation request."""
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="bypassed",
        status="active",
        steps_json="[]",
        guard_names_json="[]",
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
        is_active=True,
    )
    db.add(rec)
    db.commit()
    r = validate_run_preview_eligibility(rec.id, db)
    assert r.eligible is False
    assert any("governance" in b.lower() or "request" in b.lower() for b in r.blocking_reasons)


def test_not_eligible_llm_required(db):
    rec = _make_version(db, llm_required=True)
    _activate(db, rec)
    r = validate_run_preview_eligibility(rec.id, db)
    assert r.eligible is False
    assert any("llm" in b.lower() for b in r.blocking_reasons)


def test_checks_populated(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = validate_run_preview_eligibility(rec.id, db)
    check_names = [c.check for c in r.checks]
    assert "version_is_active" in check_names
    assert "from_agent_governance_flow" in check_names
    assert "runtime_type_safe" in check_names
    assert "llm_not_required" in check_names
    assert "preview_is_plan_only" in check_names


def test_safety_invariants(db):
    rec = _make_version(db)
    _activate(db, rec)
    r = validate_run_preview_eligibility(rec.id, db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = validate_run_preview_eligibility("nonexistent-id", db)
    assert r.eligible is False
    assert r.skill_id == ""


def test_eligible_deterministic_ui_runtime(db):
    rec = _make_version(db, runtime_type="deterministic_ui")
    _activate(db, rec)
    r = validate_run_preview_eligibility(rec.id, db)
    assert r.eligible is True
