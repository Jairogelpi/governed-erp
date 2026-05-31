from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class VisualBrowserSessionRequest(BaseModel):
    created_by: str = "operator_1"
    target_url: str = ""
    intended_erp_hint: str = ""
    workspace_mode: str = "observe_only"
    credential_capture_allowed: bool = False
    automatic_clicks_allowed: bool = False
    action_execution_allowed: bool = False


class VisualBrowserSessionRevokeRequest(BaseModel):
    actor: str = "operator_1"


class VisualBrowserSessionResponse(BaseModel):
    visual_session_id: str
    created_by: str
    target_url: str
    target_host: str
    intended_erp_hint: str
    workspace_mode: str
    status: str
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
    blocking_reasons: list[str]


class VisualBrowserSessionListResponse(BaseModel):
    sessions: list[VisualBrowserSessionResponse]


class VisualBrowserSessionAuditEventResponse(BaseModel):
    event_type: str
    visual_session_id: str
    status: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class VisualBrowserSessionAuditResponse(BaseModel):
    events: list[VisualBrowserSessionAuditEventResponse]
