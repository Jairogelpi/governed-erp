from typing import Any

from pydantic import BaseModel, Field


class PreflightActionRequest(BaseModel):
    canonical_action: str
    target_id: str


class PreflightRequest(BaseModel):
    connection_id: str | None = None
    erp_type: str | None = None
    actor: dict[str, Any]
    action: PreflightActionRequest
    policy_id: str = "formula_guard"


class ErrorResponse(BaseModel):
    error: dict[str, Any]


class PreflightResponse(BaseModel):
    preflight_id: str
    decision: str
    risk_level: str
    summary: str
    issues: list[dict[str, Any]] = Field(default_factory=list)
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    actor: dict[str, Any]
    canonical_action: str
    target_id: str
    policy_id: str
    policy_version: str
