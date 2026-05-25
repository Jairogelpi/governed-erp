"""Sprint 35 — Agent Candidate Approval Bridge unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import AgentCandidateApprovalEvent, UISkillVersionRecord
from erpguard.product.agent_candidate_approval_bridge import run_approval_bridge
from erpguard.product.agent_candidate_evidence_completeness import _REQUIRED_EVIDENCE_SOURCES


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


def _make_version(db, *, readiness_score=85, evidence_attached=True):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    promotion_readiness = {}
    if evidence_attached:
        promotion_readiness = {
            "source": "agent_handoff_packet",
            "readiness_score": readiness_score,
            "evidence_items": [
                {"source": s, "status": "passed", "label": s}
                for s in _REQUIRED_EVIDENCE_SOURCES
            ],
        }
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status="candidate",
        steps_json="[]",
        guard_names_json="[]",
        runtime_type="agent_advisory",
        promotion_readiness_json=json.dumps(promotion_readiness),
    )
    db.add(rec)
    db.commit()
    return rec


def test_bridge_completes(db):
    rec = _make_version(db)
    result = run_approval_bridge(rec.id, db)
    assert result.bridge_complete is True
    assert result.approval_packet_id != ""


def test_bridge_steps_populated(db):
    rec = _make_version(db)
    result = run_approval_bridge(rec.id, db)
    assert result.steps_total == 3
    step_names = [s.step for s in result.steps]
    assert "promotion_readiness" in step_names
    assert "evidence_completeness" in step_names
    assert "approval_packet" in step_names


def test_bridge_creates_events(db):
    rec = _make_version(db)
    run_approval_bridge(rec.id, db)
    count = db.query(AgentCandidateApprovalEvent).filter_by(version_id=rec.id).count()
    assert count >= 3


def test_safety_invariants(db):
    rec = _make_version(db)
    result = run_approval_bridge(rec.id, db)
    assert result.can_execute is False
    assert result.can_approve is False
    assert result.is_advisory_only is True


def test_version_not_found(db):
    result = run_approval_bridge("nonexistent-id", db)
    assert result.bridge_complete is False
    assert result.blocking_reason == "version_not_found"


def test_no_auto_approval(db):
    """Bridge must not approve or activate — status must remain 'candidate'."""
    rec = _make_version(db)
    run_approval_bridge(rec.id, db)
    db.refresh(rec)
    assert rec.status == "candidate"
    assert rec.is_active is False


def test_idempotent_bridge_reuses_packet(db):
    rec = _make_version(db)
    r1 = run_approval_bridge(rec.id, db)
    r2 = run_approval_bridge(rec.id, db)
    assert r1.approval_packet_id == r2.approval_packet_id
