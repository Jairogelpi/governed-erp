from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class R2WritePilotRequestBody(BaseModel):
    requested_by: dict[str, Any]
    approver_1: dict[str, Any]
    approver_2: dict[str, Any]
    target_record_id: int
    vals: dict[str, Any]
    environment: str = "staging"


class R2WritePilotRequestResponse(BaseModel):
    request_id: str
    skill_id: str
    certification_id: str | None = None
    requested_by: dict[str, Any]
    approver_1: dict[str, Any]
    approver_2: dict[str, Any]
    target_model: str
    target_record_id: int
    target_fields: list[str]
    vals: dict[str, Any]
    environment: str
    idempotency_key: str
    status: str
    allow_r2_real_write_pilot: bool = False
    allow_generic_real_odoo_writes: bool = False
    allow_r3_r4_real_writes: bool = False
    created_at: str | None = None


class R2WritePilotPolicyViolationResponse(BaseModel):
    code: str
    message: str
    blocking: bool = True


class R2WritePilotPolicyCheckResponse(BaseModel):
    request_id: str
    skill_id: str
    passed: bool
    allow_r2_real_write_pilot: bool = False
    allow_generic_real_odoo_writes: bool = False
    allow_r3_r4_real_writes: bool = False
    target_model: str
    target_model_whitelisted: bool
    target_fields: list[str]
    target_fields_whitelisted: bool
    violations: list[R2WritePilotPolicyViolationResponse] = []


class R2WritePilotRunResponse(BaseModel):
    run_id: str
    request_id: str
    skill_id: str
    status: str
    executed_action: str
    pre_snapshot: dict[str, Any] = {}
    post_snapshot: dict[str, Any] = {}
    result: dict[str, Any] = {}
    policy_passed: bool
    allow_r2_real_write_pilot: bool = False
    allow_generic_real_odoo_writes: bool = False
    allow_r3_r4_real_writes: bool = False
    created_at: str | None = None
    finished_at: str | None = None


class R2WritePilotEvidenceResponse(BaseModel):
    evidence_id: str
    run_id: str
    request_id: str
    skill_id: str
    action_taken: str
    target_model: str
    target_record_id: str
    pre_snapshot: dict[str, Any] = {}
    post_snapshot: dict[str, Any] = {}
    rollback_instructions: dict[str, Any] = {}
    idempotency_key: str
    allow_r2_real_write_pilot: bool = False
    allow_generic_real_odoo_writes: bool = False
    created_at: str | None = None
