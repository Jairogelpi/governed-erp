"""Sprint 34 — Agent Handoff Candidate Readiness unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import AgentDraftHandoffPacket
from erpguard.product.agent_handoff_candidate_builder import create_candidate_version
from erpguard.product.agent_handoff_evidence_attachment import attach_evidence_to_candidate
from erpguard.product.agent_handoff_candidate_readiness import check_candidate_readiness


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


def _make_packet(db, *, readiness_score=85):
    draft_id = str(uuid.uuid4())
    proposal_id = str(uuid.uuid4())
    packet_id = str(uuid.uuid4())
    packet_json = json.dumps({
        "sections": [
            {
                "section_id": "sec_draft",
                "title": "Draft",
                "content": {
                    "draft_id": draft_id,
                    "workflow": {"steps": [{"id": "s1", "type": "read", "description": "Read"}]},
                },
            },
            {
                "section_id": "sec_safety",
                "title": "Safety",
                "content": {"guards": [], "can_execute": False, "is_advisory_only": True},
            },
            {
                "section_id": "sec_bridge",
                "title": "Bridge",
                "content": {"review": "passed", "validation": "passed", "compile_plan": "passed"},
            },
            {
                "section_id": "sec_readiness",
                "title": "Readiness",
                "content": {
                    "overall_score": readiness_score,
                    "ready": True,
                    "checklist": [{"check_id": "chk_proof_plan", "passed": True}],
                },
            },
        ],
        "readiness_score": readiness_score,
        "ready_for_review": True,
    })
    pkt = AgentDraftHandoffPacket(
        id=packet_id, draft_id=draft_id, proposal_id=proposal_id,
        packet_json=packet_json, status="pending_human_review",
    )
    db.add(pkt)
    db.commit()
    return pkt


def test_readiness_after_evidence(db):
    pkt = _make_packet(db, readiness_score=85)
    create_candidate_version(pkt.id, db)
    attach_evidence_to_candidate(pkt.id, db)
    result = check_candidate_readiness(pkt.id, db)
    assert result.packet_id == pkt.id
    assert result.version_status == "candidate"
    assert result.evidence_attached is True


def test_no_candidate_blocking_item(db):
    pkt = _make_packet(db)
    result = check_candidate_readiness(pkt.id, db)
    assert len(result.blocking_items) > 0


def test_safety_invariants(db):
    pkt = _make_packet(db)
    create_candidate_version(pkt.id, db)
    result = check_candidate_readiness(pkt.id, db)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_can_approve_false(db):
    """can_approve must be False — candidate cannot auto-approve."""
    pkt = _make_packet(db, readiness_score=85)
    create_candidate_version(pkt.id, db)
    attach_evidence_to_candidate(pkt.id, db)
    result = check_candidate_readiness(pkt.id, db)
    assert result.can_approve is False


def test_readiness_score_range(db):
    pkt = _make_packet(db)
    create_candidate_version(pkt.id, db)
    result = check_candidate_readiness(pkt.id, db)
    assert 0 <= result.readiness_score <= 100


def test_ready_for_promotion_requires_evidence(db):
    pkt = _make_packet(db, readiness_score=85)
    create_candidate_version(pkt.id, db)
    # no attach_evidence call
    result = check_candidate_readiness(pkt.id, db)
    assert result.ready_for_promotion is False


def test_ready_for_promotion_with_evidence(db):
    pkt = _make_packet(db, readiness_score=85)
    create_candidate_version(pkt.id, db)
    attach_evidence_to_candidate(pkt.id, db)
    result = check_candidate_readiness(pkt.id, db)
    # readiness_score=85 >= 75 and evidence attached and status=candidate → ready
    assert result.ready_for_promotion is True


def test_packet_id_propagated(db):
    pkt = _make_packet(db)
    result = check_candidate_readiness(pkt.id, db)
    assert result.packet_id == pkt.id
