from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from erpguard.db.repositories import (
    create_action_dispatch_eligibility_event,
    list_recent_dispatch_eligibility_events,
)
from erpguard.product.operator_action_dispatch_eligibility import DispatchEligibilityResult


@dataclass
class DispatchAuditEntry:
    event_id: str
    action_key: str
    endpoint_hint: str
    token_id: str | None
    version_id: str | None
    eligible: bool
    blocked_reason: str | None
    policy_name: str | None
    created_at: Any


@dataclass
class DispatchAuditResult:
    entries: list[DispatchAuditEntry]
    event_count: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def persist_eligibility_event(result: DispatchEligibilityResult, session) -> str:
    """Write an immutable audit record for an eligibility check. No mutations of skill records."""
    event_id = f"adel_{uuid.uuid4().hex[:16]}"
    create_action_dispatch_eligibility_event(
        session,
        event_id=event_id,
        action_key=result.action_key,
        endpoint_hint=result.endpoint_hint,
        token_id=result.token_id,
        version_id=result.version_id,
        eligible=result.eligible,
        blocked_reason=result.blocked_reason,
        policy_name=result.policy_name,
    )
    return event_id


def get_dispatch_audit(session, *, limit: int = 50) -> DispatchAuditResult:
    """Read-only retrieval of recent dispatch eligibility events."""
    rows = list_recent_dispatch_eligibility_events(session, limit=limit)
    return DispatchAuditResult(
        entries=[
            DispatchAuditEntry(
                event_id=r.id,
                action_key=r.action_key,
                endpoint_hint=r.endpoint_hint,
                token_id=r.token_id,
                version_id=r.version_id,
                eligible=r.eligible,
                blocked_reason=r.blocked_reason,
                policy_name=r.policy_name,
                created_at=r.created_at,
            )
            for r in rows
        ],
        event_count=len(rows),
    )
