"""Sprint 40 — Skill Similarity Engine unit tests."""
from __future__ import annotations

import json
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.skill_similarity_engine import find_similar_skills


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


def _make_version(db, *, name="test", guard_names=None, steps=None):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    guard_names = guard_names or ["formula_guard"]
    steps = steps or [{"type": "read", "description": "Read"}]
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name=name,
        status="active",
        steps_json=json.dumps(steps),
        guard_names_json=json.dumps(guard_names),
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
    )
    db.add(rec)
    db.commit()
    return rec


def test_similar_returns_result(db):
    ref = _make_version(db, name="ref", guard_names=["formula_guard"])
    _make_version(db, name="similar", guard_names=["formula_guard"])
    r = find_similar_skills(ref.id, db)
    assert r.reference_version_id == ref.id
    assert r.total_found >= 1


def test_similar_excludes_self(db):
    ref = _make_version(db, name="ref", guard_names=["formula_guard"])
    r = find_similar_skills(ref.id, db)
    assert all(h.version_id != ref.id for h in r.similar)


def test_similar_scores_higher_with_more_shared_guards(db):
    ref = _make_version(db, name="ref", guard_names=["formula_guard", "access_guard"])
    _make_version(db, name="high-sim", guard_names=["formula_guard", "access_guard"])
    _make_version(db, name="low-sim", guard_names=["unrelated_guard"])
    r = find_similar_skills(ref.id, db, limit=10)
    scores = {h.name: h.similarity_score for h in r.similar}
    assert scores.get("high-sim", 0) > scores.get("low-sim", 0)


def test_similar_safety_invariants(db):
    ref = _make_version(db)
    r = find_similar_skills(ref.id, db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_similar_not_found(db):
    r = find_similar_skills("nonexistent-id", db)
    assert r.blocking_reason == "version_not_found"
    assert r.similar == []


def test_similar_hit_fields(db):
    ref = _make_version(db, name="ref", guard_names=["formula_guard"])
    _make_version(db, name="candidate", guard_names=["formula_guard"])
    r = find_similar_skills(ref.id, db)
    assert len(r.similar) >= 1
    hit = r.similar[0]
    assert isinstance(hit.similarity_score, float)
    assert isinstance(hit.shared_guards, list)
    assert "formula_guard" in hit.shared_guards


def test_similar_respects_limit(db):
    ref = _make_version(db, name="ref", guard_names=["formula_guard"])
    for i in range(5):
        _make_version(db, name=f"other-{i}", guard_names=["formula_guard"])
    r = find_similar_skills(ref.id, db, limit=2)
    assert len(r.similar) <= 2
