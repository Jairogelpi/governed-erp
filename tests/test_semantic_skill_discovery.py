"""Sprint 40 — Semantic Skill Discovery unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.semantic_skill_discovery import search_skills


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


def _make_version(db, *, name="test-skill", guard_names_json='["formula_guard"]', status="active", is_active=True):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name=name,
        status=status,
        steps_json='[{"type": "read", "description": "Read order"}]',
        guard_names_json=guard_names_json,
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
        is_active=is_active,
    )
    db.add(rec)
    db.commit()
    return rec


def test_search_returns_matching_skills(db):
    _make_version(db, name="formula-review-skill")
    r = search_skills("formula", db)
    assert r.total_found >= 1
    assert any("formula" in h.name.lower() or "formula" in str(h.guard_names).lower() for h in r.results)


def test_search_empty_query_returns_all(db):
    _make_version(db, name="skill-alpha")
    _make_version(db, name="skill-beta")
    r = search_skills("", db)
    assert r.total_found >= 2


def test_search_safety_invariants(db):
    r = search_skills("anything", db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_search_respects_limit(db):
    for i in range(5):
        _make_version(db, name=f"skill-{i}")
    r = search_skills("skill", db, limit=3)
    assert len(r.results) <= 3


def test_search_active_only_filter(db):
    _make_version(db, name="active-skill", status="active", is_active=True)
    _make_version(db, name="candidate-skill", status="candidate", is_active=False)
    r = search_skills("", db, active_only=True)
    assert all(h.is_active for h in r.results)


def test_search_status_filter(db):
    _make_version(db, name="active-skill", status="active", is_active=True)
    _make_version(db, name="candidate-skill", status="candidate", is_active=False)
    r = search_skills("", db, status_filter="candidate")
    assert all(h.status == "candidate" for h in r.results)


def test_search_hit_fields(db):
    _make_version(db, name="order-review")
    r = search_skills("order", db)
    assert r.total_found >= 1
    hit = r.results[0]
    assert hit.version_id != ""
    assert hit.skill_id != ""
    assert hit.name != ""
    assert isinstance(hit.relevance_score, float)
    assert isinstance(hit.guard_names, list)


def test_search_no_match_returns_empty(db):
    _make_version(db, name="totally-unrelated")
    r = search_skills("xyznonexistenttoken999", db)
    assert r.total_found == 0
