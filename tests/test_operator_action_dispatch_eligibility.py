"""Sprint 44 — Dispatch eligibility orchestrator tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.product.operator_action_dispatch_eligibility import check_eligibility
from erpguard.product.operator_step_preview import preview_step
from erpguard.product.operator_step_confirmation import confirm_token


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


def _check(db, endpoint="GET /v1/agent-builder/discovery/gaps/ver_1",
           method="GET", token_id=None, version_id=None, action_key=None):
    return check_eligibility(
        action_key=action_key,
        endpoint_hint=endpoint,
        method_hint=method,
        token_id=token_id,
        version_id=version_id,
        session=db,
    )


def test_read_only_eligible_without_token(db):
    r = _check(db, endpoint="GET /v1/agent-builder/discovery/gaps/ver_1", method="GET")
    assert r.eligible is True
    assert r.action_key == "check_governance_gaps"


def test_unknown_endpoint_blocked(db):
    r = _check(db, endpoint="GET /v1/some/unknown/path", method="GET")
    assert r.eligible is False
    assert r.action_key == "unknown"
    assert "known action key" in (r.blocked_reason or "").lower()


def test_activation_blocked_without_token(db):
    r = _check(db, endpoint="POST /v1/agent-candidate-activation/ver_1", method="POST")
    assert r.eligible is False
    assert r.action_key == "activate_candidate"
    assert r.requires_confirmed_token is True
    assert r.safety_tier == "activation_only"


def test_activation_blocked_unconfirmed_token(db):
    tok = preview_step(
        plan_id="aplan_x", step_number=1, step_title="t",
        endpoint_hint="POST /v1/agent-candidate-activation/v",
        method_hint="POST", severity="blocking", session=db,
    )
    r = _check(db, endpoint="POST /v1/agent-candidate-activation/ver_1",
               method="POST", token_id=tok.token_id)
    assert r.eligible is False
    assert r.token_status == "pending"


def test_activation_eligible_confirmed_token(db):
    tok = preview_step(
        plan_id="aplan_x", step_number=1, step_title="t",
        endpoint_hint="POST /v1/agent-candidate-activation/v",
        method_hint="POST", severity="blocking", session=db,
    )
    confirm_token(tok.token_id, db)
    r = _check(db, endpoint="POST /v1/agent-candidate-activation/ver_1",
               method="POST", token_id=tok.token_id)
    assert r.eligible is True
    assert r.token_status == "confirmed"


def test_action_key_provided_directly(db):
    r = _check(db, endpoint="GET /anything", method="GET", action_key="inspect_lifecycle")
    assert r.action_key == "inspect_lifecycle"
    assert r.eligible is True


def test_unknown_action_key_blocked(db):
    r = _check(db, endpoint="GET /anything", method="GET", action_key="not_in_registry")
    assert r.eligible is False
    assert "allowlist" in (r.blocked_reason or "").lower()


def test_safety_invariants(db):
    r = _check(db)
    assert r.will_execute is False
    assert r.can_execute is False
    assert r.is_advisory_only is True


def test_token_required_not_provided_blocked(db):
    r = _check(db, endpoint="POST /v1/agent-candidate-decision/ver_1", method="POST")
    assert r.eligible is False
    assert "token" in (r.blocked_reason or "").lower()
