from __future__ import annotations

from pydantic import BaseModel


class VariantSummaryResponse(BaseModel):
    variant_id: str
    sequence: list[str]
    case_count: int
    duration_seconds: float | None
    case_ids: list[str]


class TraceEventResponse(BaseModel):
    event_key: str
    event_type: str
    timestamp: str


class CaseTraceResponse(BaseModel):
    case_id: str
    object_type: str
    variant_id: str
    duration_seconds: float | None
    events: list[TraceEventResponse]
