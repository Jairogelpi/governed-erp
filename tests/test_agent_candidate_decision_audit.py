"""Sprint 36 — Agent Candidate Decision Audit unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_activation_gate_bridge import evaluate_activation_gate
from erpguard.product.agent_candidate_decision_audit import get_decision_audit
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


def test_empty_audit(db):
    rec = _make_version(db)
    r = get_decision_audit(rec.id, db)
    assert r.event_count == 0
    assert r.decision_count == 0
    assert r.events == []


def test_audit_after_decision(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = get_decision_audit(rec.id, db)
    assert r.decision_count == 1
    assert r.event_count >= 1


def test_audit_after_gate(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    before = get_decision_audit(rec.id, db).event_count
    evaluate_activation_gate(rec.id, db)
    after = get_decision_audit(rec.id, db).event_count
    assert after > before


def test_audit_event_fields(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = get_decision_audit(rec.id, db)
    for evt in r.events:
        assert evt.event_id is not None
        assert evt.version_id == rec.id
        assert evt.step is not None
        assert evt.status is not None
        assert isinstance(evt.detail, dict)
        assert evt.created_at is not None


def test_safety_flags(db):
    rec = _make_version(db)
    r = get_decision_audit(rec.id, db)
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_version_not_found_returns_empty(db):
    r = get_decision_audit("nonexistent-id", db)
    assert r.event_count == 0
    assert r.decision_count == 0
