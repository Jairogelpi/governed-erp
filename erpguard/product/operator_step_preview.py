from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from erpguard.db.repositories import create_action_plan_step_token

_TOKEN_TTL_SECONDS = 300  # 5 minutes


def _assess_risk(endpoint_hint: str, method_hint: str, severity: str) -> tuple[str, str]:
    lower = endpoint_hint.lower()
    method = method_hint.upper()

    if any(x in lower for x in ("candidate-activation", "/activate", "activation")):
        return "high", (
            "This step triggers a candidate activation. "
            "Requires verified human approval and completed governance. "
            "Irreversible without an explicit deactivation request."
        )
    if "decision" in lower and method == "POST":
        return "high", (
            "This step records a governance decision. "
            "Once committed it becomes part of the permanent audit trail."
        )
    if method == "POST" and any(x in lower for x in ("run", "preview", "execute")):
        return "medium", (
            "This step creates a preview run event. "
            "Sandboxed and read-only against production data, "
            "but it does generate an audit record."
        )
    if method == "POST":
        return "medium", (
            "This step submits data to the system and creates a new record. "
            "Review the endpoint and payload before confirming."
        )
    if method == "NONE":
        return "low", (
            "This step represents an operator decision — no system call is made automatically."
        )
    return "low", "This step is read-only. Safe to review without risk of side effects."


@dataclass
class StepPreviewResult:
    token_id: str
    plan_id: str
    step_number: int
    step_title: str
    endpoint_hint: str
    method_hint: str
    severity: str
    risk_level: str
    risk_summary: str
    status: str
    expires_at: datetime
    ttl_seconds: int
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True


def preview_step(
    *,
    plan_id: str,
    step_number: int,
    step_title: str,
    endpoint_hint: str,
    method_hint: str,
    severity: str,
    session,
) -> StepPreviewResult:
    """Generate a risk summary and a time-limited confirmation token for a single plan step."""
    risk_level, risk_summary = _assess_risk(endpoint_hint, method_hint, severity)
    token_id = f"tok_{uuid.uuid4().hex[:20]}"
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(seconds=_TOKEN_TTL_SECONDS)

    create_action_plan_step_token(
        session,
        token_id=token_id,
        plan_id=plan_id,
        step_number=step_number,
        step_title=step_title,
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        severity=severity,
        risk_level=risk_level,
        risk_summary=risk_summary,
        expires_at=expires_at,
    )

    return StepPreviewResult(
        token_id=token_id,
        plan_id=plan_id,
        step_number=step_number,
        step_title=step_title,
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        severity=severity,
        risk_level=risk_level,
        risk_summary=risk_summary,
        status="pending",
        expires_at=expires_at,
        ttl_seconds=_TOKEN_TTL_SECONDS,
    )
