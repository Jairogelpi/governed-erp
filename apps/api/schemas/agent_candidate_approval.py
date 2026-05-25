from __future__ import annotations
from pydantic import BaseModel


class AgentCandidatePromotionReadinessResponse(BaseModel):
    version_id: str
    skill_id: str
    version_status: str
    readiness_score: int
    evidence_attached: bool
    approval_packet_exists: bool
    ready_for_human_review: bool
    blocking_items: list[str]
    advisory_items: list[str]
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class EvidenceItemSchema(BaseModel):
    source: str
    status: str
    label: str
    complete: bool


class AgentCandidateEvidenceCompletenessResponse(BaseModel):
    version_id: str
    skill_id: str
    evidence_attached: bool
    complete: bool
    items_found: int
    items_required: int
    items: list[EvidenceItemSchema]
    missing_sources: list[str]
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str


class AgentCandidateRiskSummaryResponse(BaseModel):
    version_id: str
    skill_id: str
    runtime_type: str
    runtime_label: str
    llm_required: bool
    guard_names: list[str]
    guard_count: int
    risk_level: str
    risk_flags: list[str]
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str


class AgentCandidateApprovalPacketResponse(BaseModel):
    version_id: str
    skill_id: str
    approval_packet_id: str
    status: str
    readiness_score: int
    evidence_complete: bool
    risk_level: str
    guard_names: list[str]
    approval_instructions: str
    safety_note: str
    is_cached: bool
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class BridgeStepSchema(BaseModel):
    step: str
    status: str
    detail: str


class AgentCandidateApprovalBridgeResponse(BaseModel):
    version_id: str
    skill_id: str
    bridge_complete: bool
    approval_packet_id: str
    steps: list[BridgeStepSchema]
    steps_passed: int
    steps_total: int
    blocking_reason: str
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool


class ApprovalAuditEntrySchema(BaseModel):
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: str


class AgentCandidateApprovalAuditResponse(BaseModel):
    version_id: str
    skill_id: str
    approval_packet_id: str | None
    event_count: int
    events: list[ApprovalAuditEntrySchema]
    can_execute: bool
    is_advisory_only: bool
