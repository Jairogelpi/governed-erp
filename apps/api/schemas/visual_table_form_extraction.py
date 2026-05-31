from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class VisualTableFormExtractionRequest(BaseModel):
    created_by: str = "operator_1"
    workflow_trace_id: str = ""
    extraction_goal: str = ""


class VisualTableFormExtractionResponse(BaseModel):
    extraction_id: str
    visual_session_id: str
    observation_id: str
    workflow_trace_id: str
    created_by: str
    status: str
    extraction_goal: str
    table_structures: list[dict[str, Any]]
    form_structures: list[dict[str, Any]]
    button_structures: list[dict[str, Any]]
    field_candidates: list[dict[str, Any]]
    business_surface_hints: list[dict[str, Any]]
    redaction_summary: dict[str, Any]
    safety_summary: dict[str, Any]
    blocking_reasons: list[str]


class VisualTableFormExtractionListResponse(BaseModel):
    extractions: list[VisualTableFormExtractionResponse]


class VisualTableFormExtractionAuditEventResponse(BaseModel):
    event_type: str
    extraction_id: str
    visual_session_id: str
    observation_id: str
    status: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class VisualTableFormExtractionAuditResponse(BaseModel):
    events: list[VisualTableFormExtractionAuditEventResponse]
