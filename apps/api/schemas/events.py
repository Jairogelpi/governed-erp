from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class OcelImportRequest(BaseModel):
    document: dict[str, Any]
    source: str = Field(default="api", min_length=1, max_length=200)


class OcelImportResponse(BaseModel):
    created_events: int
    duplicate_events: int
    created_objects: int
    duplicate_objects: int
    shadow_deployments: int = 0
    shadow_evaluations: int = 0
    shadow_deduplications: int = 0
    shadow_failures: int = 0


class CursorRequest(BaseModel):
    connector_id: str = Field(min_length=1, max_length=128)
    stream_key: str = Field(min_length=1, max_length=200)
    value: str


class CursorResponse(BaseModel):
    connector_id: str
    stream_key: str
    value: str | None
