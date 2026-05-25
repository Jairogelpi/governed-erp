"""Sprint 35 — Agent Candidate Risk Summary unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.agent_candidate_risk_summary import get_risk_summary


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


def _make_version(db, *, runtime_type="agent_advisory", llm_required=False, guard_names=None):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    if guard_names is None:
        guard_names = ["no_generic_writes", "requires_human_review"]
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="test-candidate",
        status="candidate",
        steps_json="[]",
        guard_names_json=json.dumps(guard_names),
        runtime_type=runtime_type,
        llm_required=llm_required,
        promotion_readiness_json="{}",
    )
    db.add(rec)
    db.commit()
    return rec


def test_basic_risk_summary(db):
    rec = _make_version(db)
    result = get_risk_summary(rec.id, db)
    assert result.version_id == rec.id
    assert result.runtime_type == "agent_advisory"
    assert result.risk_level in ("low", "medium", "high")


def test_guard_names_returned(db):
    rec = _make_version(db, guard_names=["no_generic_writes", "guard_read_only"])
    result = get_risk_summary(rec.id, db)
    assert "no_generic_writes" in result.guard_names
    assert result.guard_count == 2


def test_agent_advisory_flag_in_risk_flags(db):
    rec = _make_version(db, runtime_type="agent_advisory")
    result = get_risk_summary(rec.id, db)
    assert any("agent_sourced" in f for f in result.risk_flags)


def test_llm_required_elevates_risk(db):
    rec_llm = _make_version(db, llm_required=True)
    result = get_risk_summary(rec_llm.id, db)
    assert result.risk_level in ("medium", "high")
    assert any("llm_required" in f for f in result.risk_flags)


def test_no_guards_flag(db):
    rec = _make_version(db, guard_names=[])
    result = get_risk_summary(rec.id, db)
    assert any("no_guards" in f for f in result.risk_flags)


def test_safety_invariants(db):
    rec = _make_version(db)
    result = get_risk_summary(rec.id, db)
    assert result.can_execute is False
    assert result.is_advisory_only is True


def test_version_not_found(db):
    result = get_risk_summary("nonexistent-id", db)
    assert result.risk_level == "unknown"
    assert result.blocking_reason == "version_not_found"
