"""Sprint 36 — Agent Candidate Governance Summary unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import AgentCandidateApprovalPacket, UISkillVersionRecord
from erpguard.product.agent_candidate_governance_summary import get_governance_summary
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


def _add_approval_packet(db, version_id, skill_id):
    pkt = AgentCandidateApprovalPacket(
        id=f"acap_{uuid.uuid4().hex[:16]}",
        version_id=version_id,
        skill_id=skill_id,
        packet_json="{}",
        status="pending_human_review",
    )
    db.add(pkt)
    db.commit()
    return pkt


def test_pending_status_no_decisions(db):
    rec = _make_version(db)
    r = get_governance_summary(rec.id, db)
    assert r.governance_status == "pending"
    assert r.latest_decision is None
    assert r.decision_count == 0


def test_approved_status(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = get_governance_summary(rec.id, db)
    assert r.governance_status == "approved_pending_activation"
    assert r.latest_decision == "approve"


def test_rejected_status(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "reject", "reviewer", session=db)
    r = get_governance_summary(rec.id, db)
    assert r.governance_status == "rejected"


def test_ready_for_gate_requires_all(db):
    rec = _make_version(db)
    _add_approval_packet(db, rec.id, rec.skill_id)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = get_governance_summary(rec.id, db)
    assert r.is_ready_for_activation_gate is True


def test_not_ready_without_packet(db):
    rec = _make_version(db)
    record_human_decision(rec.id, "approve", "reviewer", session=db)
    r = get_governance_summary(rec.id, db)
    assert r.is_ready_for_activation_gate is False


def test_safety_invariants(db):
    rec = _make_version(db)
    r = get_governance_summary(rec.id, db)
    assert r.can_execute is False
    assert r.can_approve is False
    assert r.is_advisory_only is True


def test_summary_notes_present(db):
    rec = _make_version(db)
    r = get_governance_summary(rec.id, db)
    assert len(r.summary_notes) > 0
    assert any("activation" in n.lower() for n in r.summary_notes)


def test_version_not_found(db):
    r = get_governance_summary("nonexistent-id", db)
    assert r.governance_status == "blocked"
    assert r.is_ready_for_activation_gate is False
