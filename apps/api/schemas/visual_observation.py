from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class VisualObservationSnapshotRequest(BaseModel):
    created_by: str = "operator_1"
    observation_source: str = "mocked_payload"
    screen_summary: dict[str, Any] = Field(default_factory=dict)
    dom_summary: dict[str, Any] = Field(default_factory=dict)
    visible_text: list[str] = Field(default_factory=list)
    tables: list[dict[str, Any]] = Field(default_factory=list)
    forms: list[dict[str, Any]] = Field(default_factory=list)
    buttons: list[dict[str, Any]] = Field(default_factory=list)
    credential_fields_detected: list[dict[str, Any]] = Field(default_factory=list)
    dangerous_action_candidates: list[dict[str, Any]] = Field(default_factory=list)


class VisualObservationSnapshotResponse(BaseModel):
    observation_id: str
    visual_session_id: str
    created_by: str
    target_url: str
    target_host: str
    status: str
    observation_source: str
    screen_summary: dict[str, Any]
    dom_summary: dict[str, Any]
    visible_text_redacted: list[str]
    detected_tables: list[dict[str, Any]]
    detected_forms: list[dict[str, Any]]
    detected_buttons: list[dict[str, Any]]
    credential_fields_detected: list[dict[str, Any]]
    dangerous_action_candidates: list[dict[str, Any]]
    redaction_summary: dict[str, Any]
    safety_summary: dict[str, Any]
    blocking_reasons: list[str]


class VisualObservationSnapshotListResponse(BaseModel):
    snapshots: list[VisualObservationSnapshotResponse]


class VisualObservationAuditEventResponse(BaseModel):
    event_type: str
    observation_id: str
    visual_session_id: str
    status: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class VisualObservationAuditResponse(BaseModel):
    events: list[VisualObservationAuditEventResponse]
