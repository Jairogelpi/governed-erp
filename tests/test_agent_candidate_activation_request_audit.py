"""Sprint 37 — Agent Candidate Activation Request Audit unit tests."""
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
from erpguard.product.agent_candidate_activation_request_audit import get_activation_request_audit
from erpguard.product.agent_candidate_final_activation_gate import evaluate_final_activation_gate
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


def _full_flow(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    evaluate_activation_gate(rec.id, db)
    create_activation_request(rec.id, "operator", session=db)
    return rec


def test_empty_audit(db):
    rec = _make_version(db)
    r = get_activation_request_audit(rec.id, db)
    assert r.event_count == 0
    assert r.events == []


def test_audit_after_request(db):
    rec = _full_flow(db)
    r = get_activation_request_audit(rec.id, db)
    assert r.event_count >= 1
    steps = [e.step for e in r.events]
    assert "activation_request_created" in steps


def test_audit_after_final_gate(db):
    rec = _full_flow(db)
    before = get_activation_request_audit(rec.id, db).event_count
    evaluate_final_activation_gate(rec.id, db)
    after = get_activation_request_audit(rec.id, db).event_count
    assert after > before


def test_event_fields(db):
    rec = _full_flow(db)
    r = get_activation_request_audit(rec.id, db)
    for evt in r.events:
        assert evt.event_id is not None
        assert evt.version_id == rec.id
        assert evt.step is not None
        assert evt.status is not None
        assert isinstance(evt.detail, dict)
        assert evt.created_at is not None


def test_safety_invariants(db):
    rec = _make_version(db)
    r = get_activation_request_audit(rec.id, db)
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = get_activation_request_audit("nonexistent-id", db)
    assert r.event_count == 0
    assert r.events == []
