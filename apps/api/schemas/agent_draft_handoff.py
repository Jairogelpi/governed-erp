from __future__ import annotations

from pydantic import BaseModel, Field


class ProofScenarioSchema(BaseModel):
    scenario_id: str
    name: str
    category: str
    description: str
    expected_outcome: str
    status: str


class DraftProofPlanResponse(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    plan_generated: bool
    scenarios: list[ProofScenarioSchema] = Field(default_factory=list)
    scenario_count: int
    input_guard_checks: list[str] = Field(default_factory=list)
    safety_note: str
    proof_is_plan_only: bool
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str | None = None


class EvidenceItemSchema(BaseModel):
    item_id: str
    source: str
    label: str
    status: str
    detail: str


class DraftProofEvidenceResponse(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    evidence_items: list[EvidenceItemSchema] = Field(default_factory=list)
    evidence_count: int
    bridge_steps_passed: int
    bridge_steps_total: int
    clarification_questions_pct: int
    clarification_mappings_pct: int
    proof_plan_generated: bool
    can_execute: bool
    is_advisory_only: bool
    blocking_reason: str | None = None


class ReadinessCheckItemSchema(BaseModel):
    check_id: str
    label: str
    passed: bool
    required: bool
    detail: str


class ApprovalReadinessResponse(BaseModel):
    draft_id: str
    proposal_id: str | None = None
    ready: bool
    overall_score: int
    checklist: list[ReadinessCheckItemSchema] = Field(default_factory=list)
    blocking_items: list[str] = Field(default_factory=list)
    advisory_items: list[str] = Field(default_factory=list)
    can_approve: bool
    can_execute: bool
    is_advisory_only: bool
    approval_note: str


class HandoffSectionSchema(BaseModel):
    section_id: str
    title: str
    content: dict


class ApprovalHandoffPacketResponse(BaseModel):
    packet_id: str
    draft_id: str
    proposal_id: str | None = None
    status: str
    sections: list[HandoffSectionSchema] = Field(default_factory=list)
    readiness_score: int
    ready_for_review: bool
    can_approve: bool
    can_execute: bool
    is_advisory_only: bool
    approval_instructions: str
    safety_note: str
    is_cached: bool


class HandoffAuditEntrySchema(BaseModel):
    event_id: str
    step: str
    status: str
    detail: dict
    created_at: str


class DraftHandoffAuditResponse(BaseModel):
    draft_id: str
    event_count: int
    events: list[HandoffAuditEntrySchema] = Field(default_factory=list)
    can_execute: bool
    is_advisory_only: bool
