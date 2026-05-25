from __future__ import annotations
from pydantic import BaseModel


class HumanDecisionRequest(BaseModel):
    decision: str
    actor: str
    rationale: str = ""


class HumanDecisionResponse(BaseModel):
    version_id: str
    skill_id: str
    decision_id: str
    decision: str
    actor: str
    rationale: str
    governance_status: str
    version_status: str
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class DecisionEntrySchema(BaseModel):
    decision_id: str
    version_id: str
    decision: str
    actor: str
    rationale: str
    governance_status: str
    created_at: str


class DecisionHistoryResponse(BaseModel):
    version_id: str
    skill_id: str
    decision_count: int
    latest_decision: str | None
    latest_governance_status: str | None
    entries: list[DecisionEntrySchema]
    can_execute: bool
    is_advisory_only: bool


class GateCheckSchema(BaseModel):
    check: str
    passed: bool
    detail: str


class ActivationGateResponse(BaseModel):
    version_id: str
    skill_id: str
    gate_passed: bool
    activation_allowed: bool
    checks: list[GateCheckSchema]
    blocking_reasons: list[str]
    latest_decision: str | None
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool
    blocking_reason: str


class GovernanceSummaryResponse(BaseModel):
    version_id: str
    skill_id: str
    version_status: str
    runtime_type: str
    approval_packet_exists: bool
    decision_count: int
    latest_decision: str | None
    governance_status: str
    governance_label: str
    is_ready_for_activation_gate: bool
    summary_notes: list[str]
    can_execute: bool
    can_approve: bool
    is_advisory_only: bool


class DecisionAuditEntrySchema(BaseModel):
    event_id: str
    version_id: str
    step: str
    status: str
    detail: dict
    created_at: str


class DecisionAuditResponse(BaseModel):
    version_id: str
    skill_id: str
    decision_count: int
    event_count: int
    events: list[DecisionAuditEntrySchema]
    can_execute: bool
    is_advisory_only: bool
