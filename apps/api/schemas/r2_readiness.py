from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class R2EvidenceReviewResponse(BaseModel):
    review_id: str
    run_id: str
    skill_id: str
    delta: dict[str, Any] = {}
    fields_changed: int
    fields_unchanged: int
    drift_detected: bool
    drift_details: list[dict[str, Any]] = []
    status: str
    rollback_instructions: dict[str, Any] = {}
    safety_invariants: dict[str, Any] = {}
    created_at: str | None = None


class R2RollbackRehearsalStepResponse(BaseModel):
    step: int
    action: str
    description: str
    execute: bool = False


class R2RollbackRehearsalResponse(BaseModel):
    rehearsal_id: str
    run_id: str
    skill_id: str
    instructions_valid: bool
    missing_fields: list[str] = []
    dry_run_steps: list[dict[str, Any]] = []
    rehearsal_passed: bool
    notes: str
    real_rollback_executed: bool = False
    safety_invariants: dict[str, Any] = {}
    created_at: str | None = None


class R2ExecutionReportResponse(BaseModel):
    report_id: str
    run_id: str
    skill_id: str
    report: dict[str, Any] = {}
    residual_risk_score: int
    risk_level: str
    status: str
    created_at: str | None = None


class R2PromotionGateCheckResponse(BaseModel):
    name: str
    passed: bool
    description: str


class R2PromotionGateResponse(BaseModel):
    gate_id: str
    run_id: str
    skill_id: str
    gate_status: str
    blocked: bool
    checks: list[R2PromotionGateCheckResponse] = []
    blocking_reasons: list[str] = []
    safety_invariants: dict[str, Any] = {}
    created_at: str | None = None
