"""Sprint 35 — Agent Candidate Promotion Readiness unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_promotion_readiness import check_candidate_promotion_readiness


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


def _make_version(db, *, status="candidate", readiness_score=85, evidence_attached=True):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    promotion_readiness = {}
    if evidence_attached:
        promotion_readiness = {
            "source": "agent_handoff_packet",
            "readiness_score": readiness_score,
            "evidence_items": [],
        }
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status=status,
        steps_json="[]",
        guard_names_json="[]",
        runtime_type="agent_advisory",
        promotion_readiness_json=json.dumps(promotion_readiness),
    )
    db.add(rec)
    db.commit()
    return rec


def test_ready_candidate(db):
    rec = _make_version(db, status="candidate", readiness_score=85, evidence_attached=True)
    result = check_candidate_promotion_readiness(rec.id, db)
    assert result.ready_for_human_review is True
    assert result.blocking_items == []
    assert result.can_execute is False
    assert result.can_approve is False
    assert result.is_advisory_only is True


def test_wrong_status_blocks(db):
    rec = _make_version(db, status="draft", evidence_attached=True)
    result = check_candidate_promotion_readiness(rec.id, db)
    assert result.ready_for_human_review is False
    assert any("status" in b for b in result.blocking_items)


def test_no_evidence_blocks(db):
    rec = _make_version(db, evidence_attached=False)
    result = check_candidate_promotion_readiness(rec.id, db)
    assert result.ready_for_human_review is False
    assert any("evidence" in b.lower() for b in result.blocking_items)


def test_low_readiness_score_blocks(db):
    rec = _make_version(db, readiness_score=40, evidence_attached=True)
    result = check_candidate_promotion_readiness(rec.id, db)
    assert result.ready_for_human_review is False
    assert any("40" in b for b in result.blocking_items)


def test_version_not_found(db):
    result = check_candidate_promotion_readiness("nonexistent-id", db)
    assert result.ready_for_human_review is False
    assert result.version_status == "not_found"


def test_advisory_items_always_present(db):
    rec = _make_version(db)
    result = check_candidate_promotion_readiness(rec.id, db)
    assert len(result.advisory_items) > 0
    assert any("human" in a.lower() for a in result.advisory_items)


def test_safety_invariants_on_ready(db):
    rec = _make_version(db)
    result = check_candidate_promotion_readiness(rec.id, db)
    assert result.can_execute is False
    assert result.can_approve is False
    assert result.is_advisory_only is True
