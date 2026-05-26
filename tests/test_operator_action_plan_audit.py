"""Sprint 42 — Action plan audit tests."""
from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from erpguard.db.base import Base
from erpguard.product.operator_action_plan_audit import get_recent_plan_audit, persist_plan_event
from erpguard.product.operator_action_plan_builder import ActionPlan
from erpguard.product.operator_action_plan_safety import ActionPlanStep


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


def _dummy_plan(plan_type: str = "prepare_for_run") -> ActionPlan:
    step = ActionPlanStep(
        step_number=1, title="t", description="d",
        endpoint_hint="GET /v1/foo", method_hint="GET",
        severity="required", prereqs_met=True,
    )
    return ActionPlan(
        plan_id="aplan_testonly1234",
        plan_type=plan_type,
        goal="test goal",
        version_id=None,
        steps=[step],
        total_steps=1,
        blocking_count=0,
        advisory_summary="No blockers.",
    )


def test_audit_empty_initially(db):
    result = get_recent_plan_audit(db)
    assert result.event_count == 0
    assert result.entries == []
    assert result.will_execute is False
    assert result.is_advisory_only is True


def test_persist_then_retrieve(db):
    plan = _dummy_plan()
    persist_plan_event(plan, db)
    result = get_recent_plan_audit(db)
    assert result.event_count == 1
    assert result.entries[0].plan_id == plan.plan_id


def test_audit_entry_fields(db):
    persist_plan_event(_dummy_plan("activate_candidate"), db)
    entry = get_recent_plan_audit(db).entries[0]
    assert entry.plan_type == "activate_candidate"
    assert entry.goal == "test goal"
    assert entry.step_count == 1
    assert entry.blocking_count == 0


def test_audit_limit(db):
    for i in range(5):
        p = _dummy_plan()
        p = ActionPlan(
            plan_id=f"aplan_{i:016x}",
            plan_type="prepare_for_run",
            goal=f"goal {i}",
            version_id=None,
            steps=p.steps,
            total_steps=1,
            blocking_count=0,
            advisory_summary="ok",
        )
        persist_plan_event(p, db)
    result = get_recent_plan_audit(db, limit=3)
    assert result.event_count == 3
