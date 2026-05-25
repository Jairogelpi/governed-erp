"""Sprint 35 — Agent Candidate Approval Audit unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_approval_audit import get_approval_audit
from erpguard.product.agent_candidate_approval_bridge import run_approval_bridge
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


def _make_version(db):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
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
        guard_names_json="[]",
        runtime_type="agent_advisory",
        promotion_readiness_json=json.dumps(promotion_readiness),
    )
    db.add(rec)
    db.commit()
    return rec


def test_empty_audit_before_bridge(db):
    rec = _make_version(db)
    result = get_approval_audit(rec.id, db)
    assert result.event_count == 0
    assert result.events == []
    assert result.approval_packet_id is None


def test_audit_populated_after_bridge(db):
    rec = _make_version(db)
    run_approval_bridge(rec.id, db)
    result = get_approval_audit(rec.id, db)
    assert result.event_count >= 3


def test_audit_events_fields(db):
    rec = _make_version(db)
    run_approval_bridge(rec.id, db)
    result = get_approval_audit(rec.id, db)
    for evt in result.events:
        assert evt.event_id is not None
        assert evt.version_id == rec.id
        assert evt.step is not None
        assert evt.status is not None
        assert isinstance(evt.detail, dict)
        assert evt.created_at is not None


def test_approval_packet_id_in_audit(db):
    rec = _make_version(db)
    bridge = run_approval_bridge(rec.id, db)
    result = get_approval_audit(rec.id, db)
    assert result.approval_packet_id == bridge.approval_packet_id


def test_safety_flags(db):
    rec = _make_version(db)
    result = get_approval_audit(rec.id, db)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_version_not_found_returns_empty(db):
    result = get_approval_audit("nonexistent-id", db)
    assert result.event_count == 0
    assert result.approval_packet_id is None
