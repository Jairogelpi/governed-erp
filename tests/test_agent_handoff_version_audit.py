"""Sprint 34 — Agent Handoff Version Audit unit tests."""
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
from erpguard.product.agent_handoff_version_audit import get_version_audit


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
                "content": {"overall_score": 80, "ready": True},
            },
        ],
        "readiness_score": 80,
        "ready_for_review": True,
    })
    pkt = AgentDraftHandoffPacket(
        id=packet_id, draft_id=draft_id, proposal_id=proposal_id,
        packet_json=packet_json, status="pending_human_review",
    )
    db.add(pkt)
    db.commit()
    return pkt


def test_empty_audit_before_candidate(db):
    pkt = _make_packet(db)
    result = get_version_audit(pkt.id, db)
    assert result.packet_id == pkt.id
    assert result.event_count == 0
    assert result.events == []


def test_audit_after_candidate_created(db):
    pkt = _make_packet(db)
    create_candidate_version(pkt.id, db)
    result = get_version_audit(pkt.id, db)
    assert result.event_count >= 1


def test_audit_events_have_required_fields(db):
    pkt = _make_packet(db)
    create_candidate_version(pkt.id, db)
    result = get_version_audit(pkt.id, db)
    for evt in result.events:
        assert evt.event_id is not None
        assert evt.packet_id == pkt.id
        assert evt.step is not None
        assert evt.status is not None
        assert isinstance(evt.detail, dict)
        assert evt.created_at is not None


def test_version_id_populated_after_candidate(db):
    pkt = _make_packet(db)
    create_candidate_version(pkt.id, db)
    result = get_version_audit(pkt.id, db)
    assert result.version_id is not None


def test_audit_grows_after_evidence(db):
    pkt = _make_packet(db)
    create_candidate_version(pkt.id, db)
    before = get_version_audit(pkt.id, db).event_count
    attach_evidence_to_candidate(pkt.id, db)
    after = get_version_audit(pkt.id, db).event_count
    assert after > before


def test_audit_safety_flags(db):
    pkt = _make_packet(db)
    result = get_version_audit(pkt.id, db)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_packet_not_found_returns_empty(db):
    result = get_version_audit("nonexistent-id", db)
    assert result.event_count == 0
    assert result.version_id is None
