from typing import Any

from pydantic import BaseModel, Field


class PreflightCaseDetailResponse(BaseModel):
    preflight_id: str
    actor: dict[str, Any]
    action: dict[str, Any]
    canonical_action: str
    canonical_object: str
    decision: str
    risk_level: str
    summary: str | None = None
    simulation: dict[str, Any] | None = None
    invariant_results: list[dict[str, Any]] = Field(default_factory=list)
    created_at: str


class AuditTrailResponse(BaseModel):
    case_id: str
    preflight_case: dict[str, Any]
    invariant_results: list[dict[str, Any]] = Field(default_factory=list)
    audit_events: list[dict[str, Any]] = Field(default_factory=list)
    execution: dict[str, Any] | None = None
