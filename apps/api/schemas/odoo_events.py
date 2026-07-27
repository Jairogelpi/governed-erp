from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OdooBridgeEventRequest(BaseModel):
    event_id: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    record_id: int = Field(gt=0)
    occurred_at: str = Field(min_length=1, max_length=100)
    values: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    historical: bool = False
    synthetic: bool = False


class OdooIngestionResponse(BaseModel):
    correlation_id: str
    created_events: int
    duplicate_events: int
    created_objects: int
    duplicate_objects: int


class OdooPollRequest(BaseModel):
    events: list[OdooBridgeEventRequest]
    cursor: str | None = None


class OdooPollResponse(BaseModel):
    events: int
    duplicates: int
    cursor: str | None
