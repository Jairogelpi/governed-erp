"""Sprint 34 — Agent Handoff Candidate Builder unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import AgentDraftHandoffPacket, AgentHandoffVersionLink, UISkillVersionRecord
from erpguard.product.agent_handoff_candidate_builder import create_candidate_version


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


def _make_packet(db):
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
                    "workflow": {
                        "steps": [{"id": "s1", "type": "read", "description": "Read data"}]
                    },
                },
            },
            {
                "section_id": "sec_safety",
                "title": "Safety",
                "content": {"guards": [], "can_execute": False, "is_advisory_only": True},
            },
            {
                "section_id": "sec_readiness",
                "title": "Readiness",
                "content": {"overall_score": 80, "ready": True},
            },
        ],
        "readiness_score": 80,
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
    return pkt


def test_creates_candidate_version(db):
    pkt = _make_packet(db)
    result = create_candidate_version(pkt.id, db)
    assert result.version_id is not None
    assert result.status == "candidate"


def test_creates_version_link(db):
    pkt = _make_packet(db)
    result = create_candidate_version(pkt.id, db)
    link = db.query(AgentHandoffVersionLink).filter_by(packet_id=pkt.id).first()
    assert link is not None
    assert link.version_id == result.version_id


def test_creates_ui_skill_version_record(db):
    pkt = _make_packet(db)
    result = create_candidate_version(pkt.id, db)
    rec = db.query(UISkillVersionRecord).filter_by(id=result.version_id).first()
    assert rec is not None
    assert rec.status == "candidate"
    assert rec.runtime_type == "agent_advisory"


def test_idempotent_second_call_returns_cached(db):
    pkt = _make_packet(db)
    r1 = create_candidate_version(pkt.id, db)
    r2 = create_candidate_version(pkt.id, db)
    assert r2.version_id == r1.version_id
    assert r2.is_cached is True


def test_idempotent_no_duplicate_records(db):
    pkt = _make_packet(db)
    create_candidate_version(pkt.id, db)
    create_candidate_version(pkt.id, db)
    count = db.query(AgentHandoffVersionLink).filter_by(packet_id=pkt.id).count()
    assert count == 1


def test_safety_invariants(db):
    pkt = _make_packet(db)
    result = create_candidate_version(pkt.id, db)
    assert result.can_execute is False
    assert result.can_approve is False
    assert result.is_advisory_only is True


def test_not_active_not_approved(db):
    pkt = _make_packet(db)
    result = create_candidate_version(pkt.id, db)
    assert result.status not in ("active", "approved")


def test_packet_id_and_skill_id_populated(db):
    pkt = _make_packet(db)
    result = create_candidate_version(pkt.id, db)
    assert result.packet_id == pkt.id
    assert result.skill_id is not None
    assert len(result.skill_id) > 0
