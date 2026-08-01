from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CanaryPolicyCreateRequest(BaseModel):
    process_key: str = Field(min_length=1)
    stable_skill_package_id: str = Field(min_length=1)
    canary_skill_package_id: str = Field(min_length=1)
    shadow_deployment_id: str = Field(min_length=1)
    percentage_basis_points: int = Field(ge=0, le=10000)
    maximum_cases: int = Field(gt=0)
    maximum_total_amount: float = Field(gt=0)
    allowed_capabilities: list[str] = Field(default_factory=list)
    maximum_amount: float = Field(gt=0)
    company_ids: list[int] = Field(default_factory=list)
    minimum_amount: float = Field(default=0.0, ge=0)
    object_types: list[str] = Field(default_factory=list)
    safety_thresholds: dict[str, Any] = Field(default_factory=dict)


class CanaryPolicyApproveRequest(BaseModel):
    approval_id: str = Field(min_length=1)


class CanaryIncidentCreateRequest(BaseModel):
    incident_type: str = Field(min_length=1)
    severity: str = Field(pattern="^(low|medium|high|critical)$")
    details: dict[str, Any] = Field(default_factory=dict)
    routing_decision_id: str | None = None
    execution_run_id: str | None = None


class CanaryIncidentResolveRequest(BaseModel):
    resolution_notes: str = Field(default="")


class CanaryPolicyResponse(BaseModel):
    id: str
    tenant_id: str
    process_key: str
    stable_skill_package_id: str
    canary_skill_package_id: str
    shadow_deployment_id: str
    status: str
    percentage_basis_points: int
    maximum_cases: int
    maximum_total_amount: float
    allowed_capabilities: list[str]
    company_ids: list[int]
    minimum_amount: float
    maximum_amount: float
    object_types: list[str]
    safety_thresholds: dict[str, Any]
    content_hash: str
    approval_scope: str
    created_by: str
    approved_by: str | None
    created_at: str
    activated_at: str | None
    paused_at: str | None
    completed_at: str | None
    aborted_at: str | None


class CanaryRoutingDecisionResponse(BaseModel):
    id: str
    canary_policy_id: str | None
    process_key: str
    business_object_key: str | None
    bucket: int | None
    selected_lane: str
    selected_skill_package_id: str | None
    selection_reason: str
    execution_run_id: str | None
    created_at: str


class CanaryIncidentResponse(BaseModel):
    id: str
    canary_policy_id: str
    incident_type: str
    severity: str
    details: dict[str, Any]
    created_at: str
    resolved_at: str | None
    resolved_by: str | None
    resolution_notes: str
