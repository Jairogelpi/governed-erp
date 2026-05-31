"""Sprint 80 - safe visual browser session shell.

This module defines the browser-first workspace contract only. It does not
launch a browser, capture screens, inspect DOM, record clicks, execute actions,
submit forms, expose credentials, use MCP, use scheduler behavior, or write.
"""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from erpguard.db.repositories import (
    create_visual_browser_session,
    create_visual_browser_session_audit_event,
    get_visual_browser_session_by_id,
    list_visual_browser_session_audit_events,
    list_visual_browser_sessions,
    update_visual_browser_session_status,
)


class VisualBrowserWorkspaceStatus(StrEnum):
    CREATED = "created"
    WAITING_FOR_USER_LOGIN = "waiting_for_user_login"
    OBSERVING_ALLOWED = "observing_allowed"
    RECORDING_ALLOWED = "recording_allowed"
    PAUSED = "paused"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    REVOKED = "revoked"


@dataclass(frozen=True)
class VisualBrowserSessionPolicy:
    allowed_workspace_modes: tuple[str, ...] = ("observe_only", "teaching_prepare")
    credential_capture_allowed: bool = False
    llm_can_see_credentials: bool = False
    automatic_clicks_allowed: bool = False
    automatic_form_submit_allowed: bool = False
    dom_observation_allowed: bool = False
    screen_capture_allowed: bool = False
    workflow_recording_allowed: bool = False
    browser_launched: bool = False
    action_execution_allowed: bool = False
    external_http_performed: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    scheduler_used: bool = False


@dataclass
class VisualBrowserSessionInput:
    created_by: str
    target_url: str = ""
    intended_erp_hint: str = ""
    workspace_mode: str = "observe_only"
    credential_capture_allowed: bool = False
    automatic_clicks_allowed: bool = False
    action_execution_allowed: bool = False


@dataclass
class VisualBrowserSession:
    visual_session_id: str
    created_by: str
    target_url: str
    target_host: str
    intended_erp_hint: str
    workspace_mode: str
    status: str
    blocking_reasons: list[str] = field(default_factory=list)
    credential_capture_allowed: bool = False
    llm_can_see_credentials: bool = False
    automatic_clicks_allowed: bool = False
    automatic_form_submit_allowed: bool = False
    dom_observation_allowed: bool = False
    screen_capture_allowed: bool = False
    workflow_recording_allowed: bool = False
    browser_launched: bool = False
    action_execution_allowed: bool = False
    external_http_performed: bool = False
    browser_control_performed: bool = False
    mcp_execution_performed: bool = False
    scheduler_used: bool = False


class VisualBrowserSessionService:
    def __init__(self, session: Session, policy: VisualBrowserSessionPolicy | None = None) -> None:
        self.session = session
        self.policy = policy or VisualBrowserSessionPolicy()

    def create_session(self, input: VisualBrowserSessionInput) -> VisualBrowserSession:
        visual_session_id = f"vbs_{uuid.uuid4().hex[:12]}"
        target_host = _target_host(input.target_url)
        self._audit(
            visual_session_id=visual_session_id,
            event_type="visual_browser_session_requested",
            status="requested",
            actor=input.created_by or "",
            details={"requested": True},
        )
        reason = self._blocking_reason(input)
        status = (
            VisualBrowserWorkspaceStatus.BLOCKED.value
            if reason
            else VisualBrowserWorkspaceStatus.CREATED.value
        )
        row = create_visual_browser_session(
            self.session,
            visual_session_id=visual_session_id,
            created_by=input.created_by or "",
            target_url=input.target_url or "",
            target_host=target_host,
            intended_erp_hint=input.intended_erp_hint or "",
            workspace_mode=input.workspace_mode or "",
            status=status,
            blocking_reasons_json=json.dumps([reason] if reason else []),
        )
        self._audit(
            visual_session_id=row.visual_session_id,
            event_type=(
                "visual_browser_session_blocked"
                if reason
                else "visual_browser_session_created"
            ),
            status=row.status,
            actor=input.created_by or "",
            details={"blocking_reasons": [reason] if reason else []},
        )
        return self._row_to_result(row)

    def get_session(self, visual_session_id: str) -> dict[str, Any] | None:
        row = get_visual_browser_session_by_id(self.session, visual_session_id)
        if row is None:
            return None
        self._audit(
            visual_session_id=row.visual_session_id,
            event_type="visual_browser_session_retrieved",
            status=row.status,
            actor=row.created_by,
            details={},
        )
        return self._row_to_dict(row)

    def list_sessions(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            self._row_to_dict(row)
            for row in list_visual_browser_sessions(self.session, limit=limit)
        ]

    def revoke_session(self, visual_session_id: str, *, actor: str) -> VisualBrowserSession | None:
        row = update_visual_browser_session_status(
            self.session,
            visual_session_id,
            status=VisualBrowserWorkspaceStatus.REVOKED.value,
        )
        if row is None:
            return None
        self._audit(
            visual_session_id=row.visual_session_id,
            event_type="visual_browser_session_revoked",
            status=row.status,
            actor=actor,
            details={"revoked": True},
        )
        return self._row_to_result(row)

    def _blocking_reason(self, input: VisualBrowserSessionInput) -> str | None:
        if not (input.created_by or "").strip():
            return "actor_required"
        if input.workspace_mode not in self.policy.allowed_workspace_modes:
            return "workspace_mode_not_allowed"
        if input.target_url and not _is_allowed_url(input.target_url):
            return "unsafe_url_scheme"
        if input.credential_capture_allowed:
            return "credential_capture_forbidden"
        if input.automatic_clicks_allowed:
            return "automatic_clicks_forbidden"
        if input.action_execution_allowed:
            return "action_execution_forbidden"
        return None

    def _audit(
        self,
        *,
        visual_session_id: str,
        event_type: str,
        status: str,
        actor: str,
        details: dict[str, Any],
    ) -> None:
        create_visual_browser_session_audit_event(
            self.session,
            visual_session_id=visual_session_id,
            event_type=event_type,
            status=status,
            actor=actor,
            details_json=json.dumps(_safe_audit_details(details), sort_keys=True),
        )

    def _row_to_result(self, row: Any) -> VisualBrowserSession:
        return VisualBrowserSession(**self._row_to_dict(row))

    def _row_to_dict(self, row: Any) -> dict[str, Any]:
        return {
            "visual_session_id": row.visual_session_id,
            "created_by": row.created_by,
            "target_url": row.target_url,
            "target_host": row.target_host,
            "intended_erp_hint": row.intended_erp_hint,
            "workspace_mode": row.workspace_mode,
            "status": row.status,
            "credential_capture_allowed": False,
            "llm_can_see_credentials": False,
            "automatic_clicks_allowed": False,
            "automatic_form_submit_allowed": False,
            "dom_observation_allowed": False,
            "screen_capture_allowed": False,
            "workflow_recording_allowed": False,
            "browser_launched": False,
            "action_execution_allowed": False,
            "external_http_performed": False,
            "browser_control_performed": False,
            "mcp_execution_performed": False,
            "scheduler_used": False,
            "blocking_reasons": json.loads(row.blocking_reasons_json),
        }


def _target_host(target_url: str) -> str:
    if not target_url:
        return ""
    return urlparse(target_url).hostname or ""


def _is_allowed_url(target_url: str) -> bool:
    parsed = urlparse(target_url)
    if parsed.scheme == "https" and parsed.hostname:
        return True
    if parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"}:
        return True
    return False


def _safe_audit_details(details: dict[str, Any]) -> dict[str, Any]:
    allowed = {"requested", "blocking_reasons", "revoked"}
    safe = {key: value for key, value in details.items() if key in allowed}
    if "blocking_reasons" in safe:
        safe["blocking_reasons"] = [_safe_reason(reason) for reason in safe["blocking_reasons"]]
    return safe


def _safe_reason(reason: str) -> str:
    return {
        "credential_capture_forbidden": "capture_forbidden",
    }.get(reason, reason)


@dataclass
class VisualBrowserSessionAuditResult:
    events: list[dict[str, Any]]


class VisualBrowserSessionAuditService:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_audit(self, limit: int = 50) -> VisualBrowserSessionAuditResult:
        return VisualBrowserSessionAuditResult(
            events=[
                {
                    "event_type": row.event_type,
                    "visual_session_id": row.visual_session_id,
                    "status": row.status,
                    "actor": row.actor,
                    "details": _safe_audit_details(json.loads(row.details_json)),
                    "created_at": row.created_at,
                }
                for row in list_visual_browser_session_audit_events(self.session, limit=limit)
            ]
        )
