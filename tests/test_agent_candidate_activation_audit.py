"""Sprint 38 — Agent Candidate Activation Audit unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_activation_audit import get_candidate_activation_audit
from erpguard.product.agent_candidate_activation_gate_bridge import evaluate_activation_gate
from erpguard.product.agent_candidate_activation_request import create_activation_request
from erpguard.product.agent_candidate_activation_service import activate_candidate_version
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
    evaluate_final_activation_gate(rec.id, db)
    activate_candidate_version(rec.id, "operator", session=db)
    return rec


def test_empty_audit(db):
    rec = _make_version(db)
    r = get_candidate_activation_audit(rec.id, db)
    assert r.event_count == 0


def test_audit_after_activation(db):
    rec = _full_flow(db)
    r = get_candidate_activation_audit(rec.id, db)
    assert r.event_count > 0
    steps = [e.step for e in r.entries]
    assert "version_activated" in steps


def test_lifecycle_events_included(db):
    rec = _full_flow(db)
    r = get_candidate_activation_audit(rec.id, db)
    assert r.lifecycle_event_count > 0
    sources = [e.source for e in r.entries]
    assert "lifecycle" in sources
    assert "activation" in sources


def test_event_fields(db):
    rec = _full_flow(db)
    r = get_candidate_activation_audit(rec.id, db)
    for entry in r.entries:
        assert entry.event_id is not None
        assert entry.version_id == rec.id
        assert entry.step is not None
        assert entry.status is not None
        assert isinstance(entry.detail, dict)
        assert entry.created_at is not None
        assert entry.source in ("activation", "lifecycle")


def test_safety_invariants(db):
    rec = _make_version(db)
    r = get_candidate_activation_audit(rec.id, db)
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_version_not_found(db):
    r = get_candidate_activation_audit("nonexistent-id", db)
    assert r.event_count == 0
    assert r.entries == []
