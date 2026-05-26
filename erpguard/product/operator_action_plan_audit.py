from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from erpguard.db.repositories import (
    create_operator_action_plan_event,
    list_recent_operator_action_plan_events,
)
from erpguard.product.operator_action_plan_builder import ActionPlan


@dataclass
class ActionPlanAuditEntry:
    plan_id: str
    plan_type: str
    goal: str
    version_id_context: str | None
    step_count: int
    blocking_count: int
    created_at: Any


@dataclass
class ActionPlanAuditResult:
    entries: list[ActionPlanAuditEntry]
    event_count: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def persist_plan_event(plan: ActionPlan, session) -> None:
    """Write an immutable audit record for a generated plan — no mutation of skill records."""
    create_operator_action_plan_event(
        session,
        plan_id=plan.plan_id,
        plan_type=plan.plan_type,
        goal=plan.goal,
        version_id_context=plan.version_id,
        step_count=plan.total_steps,
        blocking_count=plan.blocking_count,
    )


def get_recent_plan_audit(session, *, limit: int = 50) -> ActionPlanAuditResult:
    """Read-only retrieval of recent action plan events."""
    rows = list_recent_operator_action_plan_events(session, limit=limit)
    entries = [
        ActionPlanAuditEntry(
            plan_id=r.id,
            plan_type=r.plan_type,
            goal=r.goal,
            version_id_context=r.version_id_context,
            step_count=r.step_count,
            blocking_count=r.blocking_count,
            created_at=r.created_at,
        )
        for r in rows
    ]
    return ActionPlanAuditResult(entries=entries, event_count=len(entries))
