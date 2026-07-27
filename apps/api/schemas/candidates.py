from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CandidateCreateRequest(BaseModel):
    process_key: str = Field(min_length=1)
    base_version: str = Field(min_length=1)
    candidate_version: str = Field(min_length=1)
    changes: dict[str, Any]
    evidence_refs: list[str] = Field(min_length=1)
    structured_proposal: dict[str, Any] | None = None


class CandidateResponse(BaseModel):
    id: str
    process_key: str
    base_version: str
    candidate_version: str
    status: str
    changes: dict[str, Any]
    evidence_refs: list[str]
    created_by: str
    submitted_at: str | None
