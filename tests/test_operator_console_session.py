"""Sprint 41 — Operator Console Session unit tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.product.operator_console_session import get_session_history, start_console_session


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


def test_create_session(db):
    r = start_console_session("operator", db)
    assert r.session_id.startswith("ocses_")
    assert r.actor == "operator"
    assert r.query_count == 0


def test_session_safety_invariants(db):
    r = start_console_session("operator", db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_history_empty_for_new_session(db):
    r = start_console_session("operator", db)
    h = get_session_history(r.session_id, db)
    assert h.entries == []
    assert h.entry_count == 0


def test_history_safety_invariants(db):
    r = start_console_session("operator", db)
    h = get_session_history(r.session_id, db)
    assert h.will_execute is False
    assert h.can_execute is False
    assert h.is_advisory_only is True


def test_history_for_unknown_session(db):
    h = get_session_history("nonexistent-session", db)
    assert h.entries == []
    assert h.session_id == "nonexistent-session"
