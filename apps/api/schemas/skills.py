from typing import Any

from pydantic import BaseModel, Field


class SkillPackageStep(BaseModel):
    id: str
    type: str
    target: str | None = None
    selector: str | None = None
    selector_template: str | None = None
    guard: str | None = None
    model_config = {"extra": "allow"}


class SkillCreateRequest(BaseModel):
    name: str
    description: str
    runtime_type: str
    llm_required_for_repeated_runs: bool = False
    skill_package: dict[str, Any] = Field(default_factory=dict)


class SkillCreateResponse(BaseModel):
    skill_id: str
    version_id: str
    name: str
    status: str
    runtime_type: str
    llm_required_for_repeated_runs: bool


class SkillSummaryResponse(BaseModel):
    skill_id: str
    name: str
    description: str | None = None
    status: str
    created_at: str
    updated_at: str
    latest_version_id: str | None = None
    runtime_type: str | None = None
    llm_required_for_repeated_runs: bool | None = None


class SkillDetailResponse(SkillSummaryResponse):
    skill_package: dict[str, Any] = Field(default_factory=dict)
    version: str | None = None
    version_created_at: str | None = None