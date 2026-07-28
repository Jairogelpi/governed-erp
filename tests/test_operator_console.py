"""Sprint 41 — Operator Console orchestrator unit tests."""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.db.models import UISkillVersionRecord
from erpguard.product.operator_console import run_console_query
from erpguard.product.operator_console_session import start_console_session


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


def _make_active_version(db, name="formula-review"):
    vid = f"ver_{uuid.uuid4().hex[:16]}"
    rec = UISkillVersionRecord(
        id=vid,
        skill_id=f"skill_{uuid.uuid4().hex[:8]}",
        compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
        name=name,
        status="active",
        steps_json='[{"type": "read", "description": "Read order"}]',
        guard_names_json='["formula_guard"]',
        runtime_type="agent_advisory",
        promotion_readiness_json="{}",
        is_active=True,
    )
    db.add(rec)
    db.commit()
    return rec


def _make_session(db):
    return start_console_session("operator", db).session_id


def test_console_query_returns_result(db):
    sid = _make_session(db)
    r = run_console_query("¿Qué skills tengo activas?", sid, db)
    assert r.detected_intent == "list_active_skills"
    assert r.response_message != ""
    assert r.query_id.startswith("ocqry_")


def test_console_query_safety_invariants(db):
    sid = _make_session(db)
    r = run_console_query("siguiente paso seguro", sid, db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_console_query_detects_intent(db):
    sid = _make_session(db)
    r = run_console_query("qué falta para activar", sid, db)
    assert r.detected_intent == "governance_gaps"


def test_console_query_with_version_context(db):
    rec = _make_active_version(db)
    sid = _make_session(db)
    r = run_console_query("¿Cuál es el estado de esta versión?", sid, db, version_id=rec.id)
    assert r.version_id_context == rec.id


def test_console_query_produces_follow_ups(db):
    sid = _make_session(db)
    r = run_console_query("lista activa", sid, db)
    assert isinstance(r.follow_up_suggestions, list)
    assert len(r.follow_up_suggestions) <= 3


def test_console_query_persists_in_history(db):
    from erpguard.product.operator_console_session import get_session_history
    sid = _make_session(db)
    run_console_query("skills activas", sid, db)
    run_console_query("siguiente paso", sid, db)
    h = get_session_history(sid, db)
    assert h.entry_count == 2


def test_console_query_response_message_non_empty(db):
    _make_active_version(db, name="formula-review-test")
    sid = _make_session(db)
    r = run_console_query("buscar skills de formula", sid, db)
    assert len(r.response_message) > 10


def test_console_query_result_type_set(db):
    sid = _make_session(db)
    r = run_console_query("skills activas", sid, db)
    assert r.result_type in (
        "skill_list", "similar_list", "gap_list", "next_steps",
        "lifecycle_summary", "reuse_list",
    )
