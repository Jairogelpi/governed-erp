"""Sprint 43 — Step preview product module tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
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


def _preview(db, endpoint="GET /v1/foo", method="GET", severity="required"):
    return preview_step(
        plan_id="aplan_test001",
        step_number=1,
        step_title="Test step",
        endpoint_hint=endpoint,
        method_hint=method,
        severity=severity,
        session=db,
    )


def test_preview_returns_result(db):
    r = _preview(db)
    assert r.token_id.startswith("tok_")
    assert r.plan_id == "aplan_test001"
    assert r.step_number == 1


def test_preview_advisory_only(db):
    r = _preview(db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_preview_status_pending(db):
    r = _preview(db)
    assert r.status == "pending"


def test_preview_ttl_seconds(db):
    r = _preview(db)
    assert r.ttl_seconds == 300


def test_preview_expires_at_in_future(db):
    from datetime import datetime, timezone
    r = _preview(db)
    assert r.expires_at > datetime.now(timezone.utc)


def test_risk_high_for_activation(db):
    r = _preview(db, endpoint="POST /v1/agent-candidate-activation/ver_1", method="POST")
    assert r.risk_level == "high"
    assert len(r.risk_summary) > 0


def test_risk_high_for_decision_post(db):
    r = _preview(db, endpoint="POST /v1/agent-candidate-decision/ver_1", method="POST")
    assert r.risk_level == "high"


def test_risk_medium_for_preview_post(db):
    r = _preview(db, endpoint="POST /v1/agent-skill-run-preview/ver_1/run", method="POST")
    assert r.risk_level == "medium"


def test_risk_medium_for_generic_post(db):
    r = _preview(db, endpoint="POST /v1/agent-candidate-activation-request/ver_1", method="POST")
    assert r.risk_level in ("medium", "high")


def test_risk_low_for_get(db):
    r = _preview(db, endpoint="GET /v1/agent-builder/versions/ver_1", method="GET")
    assert r.risk_level == "low"


def test_risk_low_for_none_method(db):
    r = _preview(db, endpoint="(operator decision)", method="NONE")
    assert r.risk_level == "low"


def test_each_preview_generates_unique_token(db):
    t1 = _preview(db)
    t2 = _preview(db)
    assert t1.token_id != t2.token_id
