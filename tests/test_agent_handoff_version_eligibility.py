"""Sprint 34 — Agent Handoff Version Eligibility unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import AgentDraftHandoffPacket, AgentHandoffVersionLink
from erpguard.product.agent_handoff_version_eligibility import check_handoff_version_eligibility


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


def _make_packet_json(*, can_execute=False, is_advisory_only=True, readiness_score=80):
    return json.dumps({
        "sections": [
            {
                "section_id": "sec_safety",
                "title": "Safety Invariants",
                "content": {
                    "can_execute": can_execute,
                    "is_advisory_only": is_advisory_only,
                    "requires_human_review": True,
                },
            },
            {
                "section_id": "sec_readiness",
                "title": "Readiness",
                "content": {"overall_score": readiness_score, "ready": True},
            },
        ],
        "readiness_score": readiness_score,
        "ready_for_review": True,
    })


def _make_packet(db, *, status="pending_human_review", can_execute=False, is_advisory_only=True):
    draft_id = str(uuid.uuid4())
    proposal_id = str(uuid.uuid4())
    packet_id = str(uuid.uuid4())
    pkt = AgentDraftHandoffPacket(
        id=packet_id,
        draft_id=draft_id,
        proposal_id=proposal_id,
        packet_json=_make_packet_json(can_execute=can_execute, is_advisory_only=is_advisory_only),
        status=status,
    )
    db.add(pkt)
    db.commit()
    return pkt


def test_eligible_packet(db):
    pkt = _make_packet(db)
    result = check_handoff_version_eligibility(pkt.id, db)
    assert result.eligible is True
    assert result.candidate_exists is False
    assert result.can_execute is False
    assert result.is_advisory_only is True
    assert result.issues == []


def test_ineligible_wrong_status(db):
    pkt = _make_packet(db, status="draft")
    result = check_handoff_version_eligibility(pkt.id, db)
    assert result.eligible is False
    codes = [i.code for i in result.issues]
    assert any("status" in c for c in codes)


def test_ineligible_existing_link(db):
    pkt = _make_packet(db)
    link = AgentHandoffVersionLink(
        id=str(uuid.uuid4()),
        packet_id=pkt.id,
        draft_id=pkt.draft_id,
        proposal_id=pkt.proposal_id,
        version_id=str(uuid.uuid4()),
        skill_id="s_abc",
    )
    db.add(link)
    db.commit()
    result = check_handoff_version_eligibility(pkt.id, db)
    assert result.eligible is False
    assert result.candidate_exists is True
    codes = [i.code for i in result.issues]
    assert any("candidate" in c for c in codes)


def test_ineligible_safety_can_execute_true(db):
    pkt = _make_packet(db, can_execute=True, is_advisory_only=False)
    result = check_handoff_version_eligibility(pkt.id, db)
    assert result.eligible is False
    codes = [i.code for i in result.issues]
    assert any("execute" in c or "advisory" in c for c in codes)


def test_readiness_score_in_range(db):
    pkt = _make_packet(db)
    result = check_handoff_version_eligibility(pkt.id, db)
    assert 0 <= result.readiness_score <= 100


def test_packet_not_found(db):
    result = check_handoff_version_eligibility("nonexistent-id", db)
    assert result.eligible is False
    codes = [i.code for i in result.issues]
    assert any("not_found" in c or "packet" in c.lower() for c in codes)


def test_eligible_packet_status_field(db):
    pkt = _make_packet(db)
    result = check_handoff_version_eligibility(pkt.id, db)
    assert result.packet_status == "pending_human_review"
