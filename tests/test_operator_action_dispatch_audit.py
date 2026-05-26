"""Sprint 44 — Dispatch audit tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.product.operator_action_dispatch_audit import get_dispatch_audit, persist_eligibility_event
from erpguard.product.operator_action_dispatch_eligibility import DispatchEligibilityResult


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


def _dummy_result(eligible: bool = True, key: str = "check_governance_gaps") -> DispatchEligibilityResult:
    return DispatchEligibilityResult(
        action_key=key,
        endpoint_hint="GET /v1/foo",
        eligible=eligible,
        blocked_reason=None if eligible else "test block",
        policy_name="test_policy",
        requires_confirmed_token=False,
        safety_tier="read_only",
        token_id=None,
        token_status=None,
        version_id=None,
    )


def test_audit_empty_initially(db):
    r = get_dispatch_audit(db)
    assert r.event_count == 0
    assert r.will_execute is False
    assert r.is_advisory_only is True


def test_persist_and_retrieve(db):
    persist_eligibility_event(_dummy_result(), db)
    r = get_dispatch_audit(db)
    assert r.event_count == 1
    assert r.entries[0].action_key == "check_governance_gaps"


def test_entry_eligible_field(db):
    persist_eligibility_event(_dummy_result(eligible=False, key="activate_candidate"), db)
    entry = get_dispatch_audit(db).entries[0]
    assert entry.eligible is False
    assert entry.blocked_reason == "test block"


def test_audit_limit(db):
    for i in range(6):
        persist_eligibility_event(_dummy_result(), db)
    r = get_dispatch_audit(db, limit=3)
    assert r.event_count == 3


def test_event_id_has_prefix(db):
    persist_eligibility_event(_dummy_result(), db)
    entry = get_dispatch_audit(db).entries[0]
    assert entry.event_id.startswith("adel_")
