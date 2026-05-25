"""Sprint 34 — Agent Handoff Candidate Preview unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import AgentDraftHandoffPacket
from erpguard.product.agent_handoff_candidate_preview import preview_candidate_version


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
                "section_id": "sec_proposal",
                "title": "Proposal",
                "content": {"proposal_id": proposal_id, "title": "Test Proposal"},
            },
            {
                "section_id": "sec_draft",
                "title": "Draft",
                "content": {
                    "draft_id": draft_id,
                    "workflow": {
                        "steps": [
                            {"id": "s1", "type": "read", "description": "Read invoices"},
                            {"id": "s2", "type": "validate", "description": "Validate totals"},
                        ]
                    },
                },
            },
            {
                "section_id": "sec_safety",
                "title": "Safety",
                "content": {
                    "guards": ["guard_amount_limit", "guard_read_only"],
                    "can_execute": False,
                    "is_advisory_only": True,
                },
            },
            {
                "section_id": "sec_bridge",
                "title": "Bridge",
                "content": {"review": "passed", "validation": "passed", "compile_plan": "passed"},
            },
            {
                "section_id": "sec_readiness",
                "title": "Readiness",
                "content": {"overall_score": 85, "ready": True},
            },
        ],
        "readiness_score": 85,
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


def test_preview_returns_result(db):
    pkt = _make_packet(db)
    result = preview_candidate_version(pkt.id, db)
    assert result.packet_id == pkt.id
    assert result.draft_id == pkt.draft_id
    assert result.proposal_id == pkt.proposal_id


def test_preview_skill_id_format(db):
    pkt = _make_packet(db)
    result = preview_candidate_version(pkt.id, db)
    assert result.preview_skill_id.startswith("agent_")
    assert len(result.preview_skill_id) > 6


def test_preview_version_name_format(db):
    pkt = _make_packet(db)
    result = preview_candidate_version(pkt.id, db)
    assert "candidate" in result.preview_version_name


def test_preview_steps_derived(db):
    pkt = _make_packet(db)
    result = preview_candidate_version(pkt.id, db)
    assert len(result.steps) == 2
    assert result.steps[0].step_type == "read"
    assert result.steps[1].step_type == "validate"


def test_preview_guard_names(db):
    pkt = _make_packet(db)
    result = preview_candidate_version(pkt.id, db)
    assert "guard_amount_limit" in result.guard_names
    assert "guard_read_only" in result.guard_names


def test_preview_no_db_records_created(db):
    """Preview must not create any DB records."""
    from erpguard.db.models import AgentHandoffVersionLink, UISkillVersionRecord
    pkt = _make_packet(db)
    preview_candidate_version(pkt.id, db)
    assert db.query(UISkillVersionRecord).count() == 0
    assert db.query(AgentHandoffVersionLink).count() == 0


def test_preview_safety_flags(db):
    pkt = _make_packet(db)
    result = preview_candidate_version(pkt.id, db)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_preview_readiness_score(db):
    pkt = _make_packet(db)
    result = preview_candidate_version(pkt.id, db)
    assert result.readiness_score == 85
