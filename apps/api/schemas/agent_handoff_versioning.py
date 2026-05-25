from __future__ import annotations
from pydantic import BaseModel


class EligibilityIssueSchema(BaseModel):
    code: str
    message: str


class HandoffVersionEligibilityResponse(BaseModel):
    packet_id: str
    eligible: bool
    candidate_exists: bool
    packet_status: str
    readiness_score: int
    issues: list[EligibilityIssueSchema]
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool


class CandidatePreviewStepSchema(BaseModel):
    step_index: int
    step_id: str
    step_type: str
    description: str


class HandoffCandidatePreviewResponse(BaseModel):
    packet_id: str
    draft_id: str
    proposal_id: str
    preview_skill_id: str
    preview_version_name: str
    steps: list[CandidatePreviewStepSchema]
    guard_names: list[str]
    guard_display: list[str]
    evidence_summary: dict
    readiness_score: int
    would_be_status: str
    candidate_exists: bool
    existing_version_id: str | None
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class HandoffCandidateResponse(BaseModel):
    packet_id: str
    version_id: str
    skill_id: str
    version_number: int
    status: str
    draft_id: str
    proposal_id: str
    is_cached: bool
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class HandoffEvidenceAttachmentResponse(BaseModel):
    packet_id: str
    version_id: str
    evidence_attached: bool
    bridge_steps_passed: int
    bridge_steps_total: int
    proof_plan_generated: bool
    readiness_score: int
    evidence_items: list[dict]
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str


class HandoffCandidateReadinessResponse(BaseModel):
    packet_id: str
    version_id: str
    version_status: str
    evidence_attached: bool
    readiness_score: int
    ready_for_promotion: bool
    blocking_items: list[str]
    advisory_items: list[str]
    can_approve: bool
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str


class HandoffVersionAuditEntrySchema(BaseModel):
    event_id: str
    packet_id: str
    step: str
    status: str
    detail: dict
    created_at: str


class HandoffVersionAuditResponse(BaseModel):
    packet_id: str
    version_id: str | None
    event_count: int
    events: list[HandoffVersionAuditEntrySchema]
    can_execute: bool
    is_advisory_only: bool


class SourceHandoffResponse(BaseModel):
    version_id: str
    packet_id: str
    draft_id: str
    proposal_id: str
    skill_id: str
    linked_at: str
    can_execute: bool
    is_advisory_only: bool
