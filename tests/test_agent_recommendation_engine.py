"""Sprint 40 — Agent Recommendation Engine unit tests."""
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
from erpguard.product.agent_recommendation_engine import get_recommendations


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


def test_recommendations_present_for_candidate(db):
    rec = _make_version(db)
    r = get_recommendations(rec.id, db)
    assert len(r.recommendations) > 0
    assert r.governance_complete is False


def test_first_recommendation_is_decision(db):
    rec = _make_version(db)
    r = get_recommendations(rec.id, db)
    assert r.recommendations[0].action == "submit_human_decision"


def test_recommendations_reduce_after_approval(db):
    rec = _make_version(db)
    before = len(get_recommendations(rec.id, db).recommendations)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    after = len(get_recommendations(rec.id, db).recommendations)
    assert after < before


def test_governance_complete_after_full_flow(db):
    rec = _make_version(db)
    _full_activate(db, rec)
    get_run_preview(rec.id, db)
    r = get_recommendations(rec.id, db)
    assert r.governance_complete is True
    assert r.recommendations[0].action == "governance_complete"


def test_safety_invariants(db):
    rec = _make_version(db)
    r = get_recommendations(rec.id, db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = get_recommendations("nonexistent-id", db)
    assert r.blocking_reason == "version_not_found"
    assert r.recommendations == []


def test_recommendation_fields(db):
    rec = _make_version(db)
    r = get_recommendations(rec.id, db)
    rec_item = r.recommendations[0]
    assert rec_item.priority >= 1
    assert rec_item.action != ""
    assert rec_item.description != ""
    assert rec_item.endpoint_hint != ""
