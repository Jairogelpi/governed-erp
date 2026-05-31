from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VisualWorkflowTraceRequest(BaseModel):
    created_by: str = "operator_1"
    workflow_name: str = ""
    workflow_goal: str = ""
    observation_ids: list[str] = Field(default_factory=list)
    steps: list[dict[str, Any]] = Field(default_factory=list)


class VisualWorkflowTraceResponse(BaseModel):
    workflow_trace_id: str
    visual_session_id: str
    created_by: str
    status: str
    workflow_name: str
    workflow_goal: str
    observation_ids: list[str]
    steps: list[dict[str, Any]]
    dangerous_action_steps: list[dict[str, Any]]
    credential_touchpoints: list[dict[str, Any]]
    redaction_summary: dict[str, Any]
    safety_summary: dict[str, Any]
    blocking_reasons: list[str]


class VisualWorkflowTraceListResponse(BaseModel):
    traces: list[VisualWorkflowTraceResponse]


class VisualWorkflowTraceAuditEventResponse(BaseModel):
    event_type: str
    workflow_trace_id: str
    visual_session_id: str
    status: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class VisualWorkflowTraceAuditResponse(BaseModel):
    events: list[VisualWorkflowTraceAuditEventResponse]
