from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WritePilotRequestBody(BaseModel):
    requested_by: dict[str, Any]
    approver_1: dict[str, Any]
    approver_2: dict[str, Any]
    target_res_model: str
    target_res_id: int
    payload: dict[str, Any]


class WritePilotRequestResponse(BaseModel):
    request_id: str
    skill_id: str
    certification_id: str | None = None
    requested_by: dict[str, Any]
    approver_1: dict[str, Any]
    approver_2: dict[str, Any]
    target_model: str
    target_res_model: str
    target_res_id: int
    payload: dict[str, Any]
    idempotency_key: str
    status: str
    allow_r1_real_write_pilot: bool = False
    allow_generic_real_odoo_writes: bool = False
    allow_r3_r4_real_writes: bool = False
    created_at: str | None = None


class WritePilotPolicyCheckResponse(BaseModel):
    request_id: str
    skill_id: str
    passed: bool
    allow_r1_real_write_pilot: bool = False
    allow_generic_real_odoo_writes: bool = False
    allow_r3_r4_real_writes: bool = False
    target_model: str
    target_whitelisted: bool
    violations: list[dict[str, Any]]


class WritePilotRunResponse(BaseModel):
    run_id: str
    request_id: str
    skill_id: str
    status: str
    executed_action: str
    pre_snapshot: dict[str, Any]
    post_snapshot: dict[str, Any]
    result: dict[str, Any]
    policy_passed: bool
    allow_r1_real_write_pilot: bool = False
    allow_generic_real_odoo_writes: bool = False
    allow_r3_r4_real_writes: bool = False
    created_at: str | None = None
    finished_at: str | None = None


class WritePilotEvidenceResponse(BaseModel):
    evidence_id: str
    run_id: str
    request_id: str
    skill_id: str
    action_taken: str
    target_model: str
    target_res_model: str
    target_res_id: str
    pre_snapshot: dict[str, Any]
    post_snapshot: dict[str, Any]
    idempotency_key: str
    allow_r1_real_write_pilot: bool = False
    allow_generic_real_odoo_writes: bool = False
    created_at: str | None = None
