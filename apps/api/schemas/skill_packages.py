from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class WorkflowStepRequest(BaseModel):
    step_name: str = Field(min_length=1)
    capability: str = Field(min_length=1)


class SkillCompileRequest(BaseModel):
    connector_id: str = Field(min_length=1)
    workflow_steps: list[WorkflowStepRequest] = Field(default_factory=list)


class SkillPromoteCanaryRequest(BaseModel):
    shadow_deployment_id: str = Field(min_length=1)
    reason: str = Field(default="")


class SkillPromoteActiveRequest(BaseModel):
    reason: str = Field(default="")


class SkillRollbackRequest(BaseModel):
    process_key: str = Field(min_length=1)
    reason: str = Field(default="")


class ActiveSkillPackageResponse(BaseModel):
    process_key: str
    active: "SkillPackageResponse | None"


class SkillPackageResponse(BaseModel):
    id: str
    tenant_id: str
    candidate_id: str
    proof_id: str
    process_key: str
    candidate_version: str
    connector_id: str
    status: str
    package: dict[str, Any]
    validation_result: dict[str, Any]
    package_hash: str
    created_at: str
    approved_at: str | None
