"""Sprint 40 — Skill Lifecycle Summary unit tests."""
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
from erpguard.product.skill_lifecycle_summary import get_lifecycle_summary


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


def test_lifecycle_summary_for_candidate(db):
    rec = _make_version(db)
    r = get_lifecycle_summary(rec.id, db)
    assert r.version_id == rec.id
    assert r.status == "candidate"
    assert r.is_active is False
    assert r.has_human_decision is False


def test_lifecycle_summary_after_decision(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = get_lifecycle_summary(rec.id, db)
    assert r.has_human_decision is True
    assert r.human_decision == "approve"
    assert "approved" in r.governance_status


def test_lifecycle_summary_active_governed(db):
    rec = _make_version(db)
    _full_activate(db, rec)
    r = get_lifecycle_summary(rec.id, db)
    assert r.governance_status == "active_governed"
    assert r.is_active is True
    assert r.has_activation_request is True


def test_lifecycle_events_present_after_activation(db):
    rec = _make_version(db)
    _full_activate(db, rec)
    r = get_lifecycle_summary(rec.id, db)
    assert len(r.lifecycle_events) >= 1
    event_types = [e.event_type for e in r.lifecycle_events]
    assert "activated" in event_types


def test_has_run_preview_after_preview(db):
    rec = _make_version(db)
    _full_activate(db, rec)
    get_run_preview(rec.id, db)
    r = get_lifecycle_summary(rec.id, db)
    assert r.has_run_preview is True
    assert r.preview_event_count >= 1


def test_safety_invariants(db):
    rec = _make_version(db)
    r = get_lifecycle_summary(rec.id, db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = get_lifecycle_summary("nonexistent-id", db)
    assert r.blocking_reason == "version_not_found"
    assert r.governance_status == "unknown"


def test_summary_fields_populated(db):
    rec = _make_version(db)
    r = get_lifecycle_summary(rec.id, db)
    assert r.skill_id != ""
    assert r.name != ""
    assert r.runtime_type != ""
