"""Sprint 35 — Agent Candidate Approval Packet unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import AgentCandidateApprovalPacket, UISkillVersionRecord
from erpguard.product.agent_candidate_approval_packet import create_approval_packet
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


def _make_version(db, *, with_evidence=True):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    promotion_readiness = {}
    if with_evidence:
        promotion_readiness = {
            "source": "agent_handoff_packet",
            "readiness_score": 85,
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
        guard_names_json=json.dumps(["no_generic_writes", "requires_human_review"]),
        runtime_type="agent_advisory",
        promotion_readiness_json=json.dumps(promotion_readiness),
    )
    db.add(rec)
    db.commit()
    return rec


def test_creates_approval_packet(db):
    rec = _make_version(db)
    result = create_approval_packet(rec.id, db)
    assert result.approval_packet_id != ""
    assert result.status == "pending_human_review"


def test_packet_persisted_in_db(db):
    rec = _make_version(db)
    result = create_approval_packet(rec.id, db)
    pkt = db.query(AgentCandidateApprovalPacket).filter_by(version_id=rec.id).first()
    assert pkt is not None
    assert pkt.id == result.approval_packet_id


def test_idempotent_returns_cached(db):
    rec = _make_version(db)
    r1 = create_approval_packet(rec.id, db)
    r2 = create_approval_packet(rec.id, db)
    assert r2.approval_packet_id == r1.approval_packet_id
    assert r2.is_cached is True


def test_idempotent_no_duplicate_packets(db):
    rec = _make_version(db)
    create_approval_packet(rec.id, db)
    create_approval_packet(rec.id, db)
    count = db.query(AgentCandidateApprovalPacket).filter_by(version_id=rec.id).count()
    assert count == 1


def test_safety_invariants(db):
    rec = _make_version(db)
    result = create_approval_packet(rec.id, db)
    assert result.can_execute is False
    assert result.can_approve is False
    assert result.is_advisory_only is True


def test_approval_instructions_present(db):
    rec = _make_version(db)
    result = create_approval_packet(rec.id, db)
    assert "human" in result.approval_instructions.lower()
    assert "approve" in result.approval_instructions.lower()


def test_safety_note_contains_invariants(db):
    rec = _make_version(db)
    result = create_approval_packet(rec.id, db)
    assert "can_execute=False" in result.safety_note


def test_version_not_found(db):
    result = create_approval_packet("nonexistent-id", db)
    assert result.approval_packet_id == ""
    assert result.blocking_reason == "version_not_found"
