from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from erpguard.db.repositories import (
    confirm_action_plan_step_token,
    expire_action_plan_step_tokens,
    get_action_plan_step_token,
)


@dataclass
class TokenStatusResult:
    token_id: str
    plan_id: str
    step_number: int
    step_title: str
    risk_level: str
    status: str        # pending | confirmed | expired
    expires_at: Any
    confirmed_at: Any
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


@dataclass
class ConfirmTokenResult:
    token_id: str
    plan_id: str
    step_number: int
    step_title: str
    status: str        # confirmed | already_confirmed | expired | not_found
    confirmed_at: Any
    message: str
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def get_token_status(token_id: str, session) -> TokenStatusResult | None:
    """Read token status — also expires stale pending tokens on the way."""
    expire_action_plan_step_tokens(session, now=datetime.now(timezone.utc))
    row = get_action_plan_step_token(session, token_id)
    if row is None:
        return None
    return TokenStatusResult(
        token_id=row.id,
        plan_id=row.plan_id,
        step_number=row.step_number,
        step_title=row.step_title,
        risk_level=row.risk_level,
        status=row.status,
        expires_at=row.expires_at,
        confirmed_at=row.confirmed_at,
    )


def confirm_token(token_id: str, session) -> ConfirmTokenResult:
    """Operator explicitly confirms a step token. Does NOT execute anything."""
    expire_action_plan_step_tokens(session, now=datetime.now(timezone.utc))
    row = get_action_plan_step_token(session, token_id)

    if row is None:
        return ConfirmTokenResult(
            token_id=token_id,
            plan_id="",
            step_number=0,
            step_title="",
            status="not_found",
            confirmed_at=None,
            message="Token not found. Request a new step preview.",
        )

    if row.status == "confirmed":
        return ConfirmTokenResult(
            token_id=token_id,
            plan_id=row.plan_id,
            step_number=row.step_number,
            step_title=row.step_title,
            status="already_confirmed",
            confirmed_at=row.confirmed_at,
            message="Token already confirmed. Each token can only be used once.",
        )

    if row.status == "expired":
        return ConfirmTokenResult(
            token_id=token_id,
            plan_id=row.plan_id,
            step_number=row.step_number,
            step_title=row.step_title,
            status="expired",
            confirmed_at=None,
            message="Token has expired. Request a new step preview to get a fresh token.",
        )

    now = datetime.now(timezone.utc)
    updated = confirm_action_plan_step_token(session, token_id, confirmed_at=now)
    assert updated is not None  # token was just verified to exist above
    return ConfirmTokenResult(
        token_id=token_id,
        plan_id=updated.plan_id,
        step_number=updated.step_number,
        step_title=updated.step_title,
        status="confirmed",
        confirmed_at=updated.confirmed_at,
        message=(
            f"Step {updated.step_number} '{updated.step_title}' confirmed by operator. "
            "No action has been executed. This record is advisory only."
        ),
    )
