"""Sprint 40 — Skill Reuse Suggester unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.skill_reuse_suggester import get_reuse_suggestions


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


def _make_active_version(db, *, name="active-skill", guard_names=None):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    guard_names = guard_names or ["formula_guard"]
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name=name,
        status="active",
        steps_json='[{"type": "read", "description": "Read"}]',
        guard_names_json=json.dumps(guard_names),
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
        is_active=True,
    )
    db.add(rec)
    db.commit()
    return rec


def test_reuse_suggestions_returns_active_skills(db):
    _make_active_version(db, name="formula-review")
    r = get_reuse_suggestions(db, query="formula")
    assert r.total_found >= 1
    assert all(s.is_active for s in r.suggestions)


def test_reuse_safety_invariants(db):
    r = get_reuse_suggestions(db, query="any")
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_reuse_returns_empty_when_no_active_versions(db):
    r = get_reuse_suggestions(db, query="formula")
    assert r.total_found == 0


def test_reuse_respects_limit(db):
    for i in range(5):
        _make_active_version(db, name=f"formula-skill-{i}", guard_names=["formula_guard"])
    r = get_reuse_suggestions(db, query="formula", limit=2)
    assert len(r.suggestions) <= 2


def test_reuse_suggestion_fields(db):
    _make_active_version(db, name="formula-review")
    r = get_reuse_suggestions(db, query="formula")
    assert r.total_found >= 1
    s = r.suggestions[0]
    assert s.version_id != ""
    assert s.name != ""
    assert s.reuse_rationale != ""
    assert s.next_step != ""
    assert isinstance(s.similarity_score, float)


def test_reuse_with_version_id_reference(db):
    ref = _make_active_version(db, name="ref-skill", guard_names=["formula_guard"])
    target = _make_active_version(db, name="target-skill", guard_names=["formula_guard"])
    r = get_reuse_suggestions(db, version_id=ref.id, limit=10)
    version_ids = [s.version_id for s in r.suggestions]
    assert target.id in version_ids
    assert ref.id not in version_ids


def test_reuse_excludes_inactive_skills(db):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    inactive = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name="inactive-formula-skill",
        status="candidate",
        steps_json="[]",
        guard_names_json='["formula_guard"]',
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
        is_active=False,
    )
    db.add(inactive)
    db.commit()
    r = get_reuse_suggestions(db, query="formula")
    assert all(s.is_active for s in r.suggestions)
