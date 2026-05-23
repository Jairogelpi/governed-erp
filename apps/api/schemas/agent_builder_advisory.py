from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CreateAdvisorySessionRequest(BaseModel):
    created_by: dict[str, Any] = Field(default_factory=dict)


class AdvisorySessionResponse(BaseModel):
    session_id: str
    status: str
    request_text: str = ""
    latest_proposal_id: str | None = None
    created_by: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    updated_at: str | None = None
    is_advisory_only: bool = True
    can_execute: bool = False


class ProposeRequest(BaseModel):
    request_text: str


class ReviseRequest(BaseModel):
    updated_request: str


class AdvisoryProposalResponse(BaseModel):
    proposal_id: str
    session_id: str
    request_text: str
    intent: dict[str, Any] = Field(default_factory=dict)
    process_category: str = "unknown"
    process_description: str = ""
    entity_mappings: list[dict[str, Any]] = Field(default_factory=list)
    workflow: dict[str, Any] = Field(default_factory=dict)
    guards: dict[str, Any] = Field(default_factory=dict)
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    clarification_questions: list[dict[str, Any]] = Field(default_factory=list)
    revision_number: int = 1
    status: str = "draft"
    is_advisory_only: bool = True
    can_execute: bool = False
    safety_note: str = ""
    created_at: str | None = None


class ProposalSafetyResponse(BaseModel):
    proposal_id: str
    is_advisory_only: bool = True
    can_execute: bool = False
    risk_summary: dict[str, Any] = Field(default_factory=dict)
    guard_summary: dict[str, Any] = Field(default_factory=dict)
    safety_invariants: list[str] = Field(default_factory=list)
