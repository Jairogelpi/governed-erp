"""Sprint 34 — Agent Handoff Evidence Attachment unit tests."""
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


def _make_packet(db, *, bridge_passed=True):
    draft_id = str(uuid.uuid4())
    proposal_id = str(uuid.uuid4())
    packet_id = str(uuid.uuid4())
    bridge_status = "passed" if bridge_passed else "failed"
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
                "content": {
                    "guards": ["guard_read_only"],
                    "can_execute": False,
                    "is_advisory_only": True,
                },
            },
            {
                "section_id": "sec_bridge",
                "title": "Bridge",
                "content": {
                    "review": bridge_status,
                    "validation": bridge_status,
                    "compile_plan": bridge_status,
                },
            },
            {
                "section_id": "sec_readiness",
                "title": "Readiness",
                "content": {
                    "overall_score": 90,
                    "ready": True,
                    "checklist": [{"check_id": "chk_proof_plan", "passed": True}],
                },
            },
        ],
        "readiness_score": 90,
        "ready_for_review": True,
    })
    pkt = AgentDraftHandoffPacket(
        id=packet_id,
        draft_id=draft_id,
        proposal_id=proposal_id,
        packet_json=packet_json,
        status="pending_human_review",
    )
    db.add(pkt)
    db.commit()
    create_candidate_version(packet_id, db)
    return pkt


def test_attach_returns_result(db):
    pkt = _make_packet(db)
    result = attach_evidence_to_candidate(pkt.id, db)
    assert result.packet_id == pkt.id
    assert result.evidence_attached is True


def test_evidence_items_populated(db):
    pkt = _make_packet(db)
    result = attach_evidence_to_candidate(pkt.id, db)
    assert len(result.evidence_items) > 0


def test_bridge_steps_reported(db):
    pkt = _make_packet(db, bridge_passed=True)
    result = attach_evidence_to_candidate(pkt.id, db)
    assert result.bridge_steps_total == 3
    assert result.bridge_steps_passed == 3


def test_readiness_score_non_negative(db):
    pkt = _make_packet(db)
    result = attach_evidence_to_candidate(pkt.id, db)
    assert result.readiness_score >= 0


def test_safety_flags(db):
    pkt = _make_packet(db)
    result = attach_evidence_to_candidate(pkt.id, db)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_proof_plan_generated(db):
    pkt = _make_packet(db)
    result = attach_evidence_to_candidate(pkt.id, db)
    assert result.proof_plan_generated is True


def test_no_candidate_returns_not_attached(db):
    """Evidence attachment without a prior candidate should signal not attached."""
    draft_id = str(uuid.uuid4())
    proposal_id = str(uuid.uuid4())
    packet_id = str(uuid.uuid4())
    packet_json = json.dumps({
        "sections": [],
        "readiness_score": 0,
        "ready_for_review": False,
    })
    pkt = AgentDraftHandoffPacket(
        id=packet_id, draft_id=draft_id, proposal_id=proposal_id,
        packet_json=packet_json, status="pending_human_review",
    )
    db.add(pkt)
    db.commit()
    result = attach_evidence_to_candidate(packet_id, db)
    assert result.evidence_attached is False
