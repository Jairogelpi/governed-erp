from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunPlanRequest(BaseModel):
    connection_id: str = Field(min_length=1)
    skill_package_id: str = Field(min_length=1)
    capability: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)
    capability_payload: dict[str, Any] = Field(default_factory=dict)


class RunApproveRequest(BaseModel):
    approval_ids: list[str] = Field(default_factory=list)
    ttl_seconds: int = 900


class ApprovalCreateRequest(BaseModel):
    scope: str = Field(min_length=1)


class ApprovalResponse(BaseModel):
    id: str
    tenant_id: str
    actor_id: str
    scope: str
    created_at: str
    used_at: str | None
    used_by_run_id: str | None


class KillSwitchRequest(BaseModel):
    active: bool


class KillSwitchResponse(BaseModel):
    tenant_id: str
    active: bool
    updated_at: str


class RunResponse(BaseModel):
    id: str
    tenant_id: str
    actor_id: str
    connection_id: str
    connector_id: str
    skill_package_id: str
    process_version_id: str
    skill_version_id: str
    capability: str
    operation_hash: str
    native_plan_hash: str
    state_snapshot_hash: str
    capability_allowlist: list[str]
    approval_ids: list[str]
    idempotency_key: str
    status: str
    created_at: str
    approved_at: str | None
    expires_at: str | None
    executed_at: str | None
    revoked_at: str | None
    verification_result: dict[str, Any] | None
