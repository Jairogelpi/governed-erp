"""Sprint 38 — Agent Candidate Post-Activation Summary unit tests."""
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
from erpguard.product.agent_candidate_post_activation_summary import get_post_activation_summary


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


def _full_flow(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    create_activation_request(rec.id, "operator", session=db)
    evaluate_final_activation_gate(rec.id, db)
    activate_candidate_version(rec.id, "operator", session=db)
    return rec


def test_summary_after_activation(db):
    rec = _full_flow(db)
    r = get_post_activation_summary(rec.id, db)
    assert r.version_status == "active"
    assert r.is_active is True
    assert r.governance_status == "active_governed"


def test_summary_not_executed(db):
    rec = _full_flow(db)
    r = get_post_activation_summary(rec.id, db)
    assert r.is_executed is False
    assert r.can_execute is False


def test_summary_notes_present(db):
    rec = _full_flow(db)
    r = get_post_activation_summary(rec.id, db)
    assert len(r.summary_notes) > 0
    assert any("execution" in n.lower() for n in r.summary_notes)


def test_summary_before_activation(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = get_post_activation_summary(rec.id, db)
    assert r.governance_status == "approved_pending_activation"
    assert r.is_active is False


def test_safety_invariants(db):
    rec = _full_flow(db)
    r = get_post_activation_summary(rec.id, db)
    assert r.can_execute is False
    assert r.can_approve is False
    assert r.is_advisory_only is True


def test_request_id_in_summary(db):
    rec = _full_flow(db)
    r = get_post_activation_summary(rec.id, db)
    assert r.request_id != ""
    assert r.request_status == "pending_review"


def test_version_not_found(db):
    r = get_post_activation_summary("nonexistent-id", db)
    assert r.governance_status == "blocked"
    assert r.is_active is False
