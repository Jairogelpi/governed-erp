from typing import Any

from pydantic import BaseModel, Field


class NativeActionRequest(BaseModel):
    model: str | None = None
    method: str | None = None
    record_id: int | str | None = None


class PreflightActionRequest(BaseModel):
    canonical_action: str
    canonical_object: str | None = None
    native: NativeActionRequest | None = None
    target_id: str | None = None


class PreflightOptionsRequest(BaseModel):
    simulate: bool = True
    allow_write: bool = False


class PreflightRequest(BaseModel):
    connection_id: str | None = None
    erp_type: str | None = None
    actor: dict[str, Any]
    action: PreflightActionRequest
    options: PreflightOptionsRequest = Field(default_factory=PreflightOptionsRequest)
    policy_id: str = "formula_guard"


class ErrorResponse(BaseModel):
    error: dict[str, Any]


class PreflightResponse(BaseModel):
    preflight_id: str
    decision: str
    risk_level: str
    summary: str
    blocking_issues: list[dict[str, Any]] = Field(default_factory=list)
    issues: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    predicted_impact: dict[str, Any] = Field(default_factory=dict)
    approval_required: bool
    actor: dict[str, Any]
    canonical_action: str
    canonical_object: str
    target_id: str
    policy_id: str
    policy_version: str
