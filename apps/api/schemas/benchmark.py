from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BenchmarkRunCreateRequest(BaseModel):
    dataset_version: str = Field(min_length=1)
    configurations: list[str] = Field(min_length=1)
    repeats: int = Field(default=1, ge=1, le=20)


class BenchmarkRunResponse(BaseModel):
    id: str
    tenant_id: str
    dataset_version: str
    dataset_manifest_hash: str
    configurations: list[str]
    repeats: int
    status: str
    created_by: str
    started_at: str
    completed_at: str | None


class BenchmarkReportResponse(BaseModel):
    dataset_version: str
    disclaimer: str
    configurations: dict[str, Any]
    comparison: dict[str, Any]
