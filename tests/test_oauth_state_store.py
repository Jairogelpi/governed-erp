from __future__ import annotations

import time
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from erpguard.db.base import Base
from erpguard.product.oauth_state_store import OAuthStateStore


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    s = Session()
    yield s
    s.close()


def _store(session) -> OAuthStateStore:
    return OAuthStateStore(session)


def test_create_state_returns_record(session):
    store = _store(session)
    record = store.create(
        profile_id="p1",
        connector_id="google_calendar_readonly",
        redirect_uri="http://localhost:8000/callback",
        scope_requested="https://www.googleapis.com/auth/calendar.readonly",
    )
    assert record.state_token
    assert len(record.state_token) > 20
    assert record.profile_id == "p1"
    assert record.status == "pending"
    assert record.is_valid


def test_get_state_by_token(session):
    store = _store(session)
    created = store.create(
        profile_id="p2",
        connector_id="google_calendar_readonly",
        redirect_uri="http://localhost:8000/callback",
        scope_requested="https://www.googleapis.com/auth/calendar.readonly",
    )
    retrieved = store.get(created.state_token)
    assert retrieved is not None
    assert retrieved.state_token == created.state_token
    assert retrieved.profile_id == "p2"


def test_get_nonexistent_state_returns_none(session):
    store = _store(session)
    assert store.get("nonexistent_state_token_xyz") is None


def test_consume_marks_state_used(session):
    store = _store(session)
    record = store.create(
        profile_id="p3",
        connector_id="google_calendar_readonly",
        redirect_uri="http://localhost:8000/callback",
        scope_requested="https://www.googleapis.com/auth/calendar.readonly",
    )
    consumed = store.consume(record.state_token)
    assert consumed is not None
    assert consumed.status == "used"
    assert consumed.used_at is not None


def test_consume_second_time_returns_none(session):
    store = _store(session)
    record = store.create(
        profile_id="p4",
        connector_id="google_calendar_readonly",
        redirect_uri="http://localhost:8000/callback",
        scope_requested="https://www.googleapis.com/auth/calendar.readonly",
    )
    store.consume(record.state_token)
    # Second consume of same token must fail
    result = store.consume(record.state_token)
    assert result is None


def test_state_token_is_unique_per_call(session):
    store = _store(session)
    r1 = store.create(profile_id="p5", connector_id="google_calendar_readonly",
                      redirect_uri="http://localhost/cb", scope_requested="scope")
    r2 = store.create(profile_id="p5", connector_id="google_calendar_readonly",
                      redirect_uri="http://localhost/cb", scope_requested="scope")
    assert r1.state_token != r2.state_token


def test_model_dump_has_required_keys(session):
    store = _store(session)
    record = store.create(profile_id="p6", connector_id="google_calendar_readonly",
                          redirect_uri="http://localhost/cb",
                          scope_requested="https://www.googleapis.com/auth/calendar.readonly")
    d = record.model_dump()
    for key in ("id", "state_token", "profile_id", "connector_id", "redirect_uri",
                "scope_requested", "status", "created_at", "expires_at"):
        assert key in d
