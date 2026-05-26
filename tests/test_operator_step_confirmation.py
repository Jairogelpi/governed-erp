"""Sprint 43 — Step confirmation product module tests."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.product.operator_step_confirmation import confirm_token, get_token_status
from erpguard.product.operator_step_preview import preview_step


@pytest.fixture()
def db():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def _make_token(db) -> str:
    r = preview_step(
        plan_id="aplan_test001",
        step_number=1,
        step_title="Verify version",
        endpoint_hint="GET /v1/foo",
        method_hint="GET",
        severity="required",
        session=db,
    )
    return r.token_id


def test_get_status_not_found(db):
    result = get_token_status("tok_nonexistent", db)
    assert result is None


def test_get_status_pending(db):
    tid = _make_token(db)
    result = get_token_status(tid, db)
    assert result.status == "pending"
    assert result.token_id == tid


def test_get_status_advisory_only(db):
    tid = _make_token(db)
    result = get_token_status(tid, db)
    assert result.will_execute is False
    assert result.is_advisory_only is True


def test_confirm_token_success(db):
    tid = _make_token(db)
    result = confirm_token(tid, db)
    assert result.status == "confirmed"
    assert result.confirmed_at is not None
    assert result.will_execute is False
    assert result.is_advisory_only is True


def test_confirm_token_message_references_step(db):
    tid = _make_token(db)
    result = confirm_token(tid, db)
    assert "advisory" in result.message.lower() or "confirmed" in result.message.lower()


def test_confirm_token_not_found(db):
    result = confirm_token("tok_does_not_exist", db)
    assert result.status == "not_found"


def test_confirm_token_already_confirmed(db):
    tid = _make_token(db)
    confirm_token(tid, db)
    result = confirm_token(tid, db)
    assert result.status == "already_confirmed"


def test_token_status_after_confirm(db):
    tid = _make_token(db)
    confirm_token(tid, db)
    status = get_token_status(tid, db)
    assert status.status == "confirmed"
    assert status.confirmed_at is not None


def test_expired_token_cannot_be_confirmed(db):
    from erpguard.db.repositories import get_action_plan_step_token
    tid = _make_token(db)
    # Manually expire it
    row = get_action_plan_step_token(db, tid)
    row.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.commit()
    result = confirm_token(tid, db)
    assert result.status == "expired"
