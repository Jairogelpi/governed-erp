"""Sprint 35 — Agent Candidate Evidence Completeness unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_evidence_completeness import (
    check_evidence_completeness,
    _REQUIRED_EVIDENCE_SOURCES,
)


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


def _make_version(db, *, evidence_items=None, source="agent_handoff_packet"):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    if evidence_items is None:
        evidence_items = [
            {"source": s, "status": "passed", "label": s}
            for s in _REQUIRED_EVIDENCE_SOURCES
        ]
    promotion_readiness = {
        "source": source,
        "readiness_score": 85,
        "evidence_items": evidence_items,
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


def test_complete_evidence(db):
    rec = _make_version(db)
    result = check_evidence_completeness(rec.id, db)
    assert result.complete is True
    assert result.evidence_attached is True
    assert result.missing_sources == []


def test_missing_items_reported(db):
    rec = _make_version(db, evidence_items=[
        {"source": "bridge_review", "status": "passed", "label": "review"},
    ])
    result = check_evidence_completeness(rec.id, db)
    assert result.complete is False
    assert len(result.missing_sources) > 0


def test_no_evidence_returns_incomplete(db):
    rec = _make_version(db, evidence_items=[], source="none")
    result = check_evidence_completeness(rec.id, db)
    assert result.complete is False
    assert result.evidence_attached is False


def test_items_required_matches_constant(db):
    rec = _make_version(db)
    result = check_evidence_completeness(rec.id, db)
    assert result.items_required == len(_REQUIRED_EVIDENCE_SOURCES)


def test_items_found_correct(db):
    rec = _make_version(db)
    result = check_evidence_completeness(rec.id, db)
    assert result.items_found == len(_REQUIRED_EVIDENCE_SOURCES)


def test_version_not_found(db):
    result = check_evidence_completeness("nonexistent-id", db)
    assert result.complete is False
    assert result.evidence_attached is False


def test_safety_flags(db):
    rec = _make_version(db)
    result = check_evidence_completeness(rec.id, db)
    assert result.can_execute is False
    assert result.is_advisory_only is True
