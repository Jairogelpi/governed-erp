from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class DraftPreviewResponse(BaseModel):
    proposal_id: str
    eligible: bool
    eligibility: dict[str, Any] = Field(default_factory=dict)
    mapping_completeness: dict[str, Any] = Field(default_factory=dict)
    safety_policy: dict[str, Any] = Field(default_factory=dict)
    draft_name: str = ""
    draft_description: str = ""
    draft_runtime_mode: str = "dry_run_only"
    draft_write_actions: bool = False
    draft_status: str = "pending_review"
    workflow_steps: list[dict[str, Any]] = Field(default_factory=list)
    guard_ids: list[str] = Field(default_factory=list)
    risk_level: str = "unknown"
    ready_to_create: bool = False
    blocking_issues: list[str] = Field(default_factory=list)
    advisory_note: str = ""


class CreateDraftResponse(BaseModel):
    draft_id: str
    proposal_id: str
    link_id: str
    name: str = ""
    description: str = ""
    status: str = "pending_review"
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    created_at: str | None = None
    safety: dict[str, Any] = Field(default_factory=dict)
    next_step: str = "human_review"
    advisory_note: str = ""


class DraftLinkResponse(BaseModel):
    proposal_id: str
    draft_id: str | None = None
    link_id: str | None = None
    has_draft: bool = False
    created_at: str | None = None
    message: str | None = None


class SourceProposalResponse(BaseModel):
    draft_id: str
    proposal_id: str
    session_id: str
    link_id: str
    proposal: dict[str, Any] = Field(default_factory=dict)
