from __future__ import annotations

from pydantic import BaseModel


class CreateVersionRequest(BaseModel):
    skill_id: str | None = None
    replay_run_id: str | None = None


class VersionDetailResponse(BaseModel):
    version_id: str
    skill_id: str
    compiled_skill_id: str
    version_number: int
    name: str
    status: str
    steps: list[dict]
    guard_names: list[str]
    replay_run_id: str | None
    promotion_readiness: dict
    llm_required: bool
    runtime_type: str
    is_active: bool
    created_at: str
    updated_at: str


class PromotionReadinessResponse(BaseModel):
    version_id: str
    ready: bool
    readiness_level: str
    checks: list[dict]
    blocking_reasons: list[str]
    warnings: list[str]


class LifecycleTransitionRequest(BaseModel):
    actor: str = "system"
    reason: str = ""


class LifecycleTransitionResponse(BaseModel):
    version_id: str
    skill_id: str
    from_status: str
    to_status: str
    event_type: str
    actor: str
    reason: str


class ActivationGateResponse(BaseModel):
    version_id: str
    can_activate: bool
    gate_status: str
    checks: list[dict]
    blocking_reasons: list[str]
    warnings: list[str]


class StepDiffResponse(BaseModel):
    step_id: str
    change_type: str
    from_value: dict | None
    to_value: dict | None


class CompareVersionsRequest(BaseModel):
    version_id_a: str
    version_id_b: str


class VersionComparisonResponse(BaseModel):
    version_id_a: str
    version_id_b: str
    version_number_a: int
    version_number_b: int
    steps_added: list[StepDiffResponse]
    steps_removed: list[StepDiffResponse]
    steps_changed: list[StepDiffResponse]
    guards_added: list[str]
    guards_removed: list[str]
    selectors_changed: list[dict]
    is_identical: bool
    summary: str


class RollbackPlanResponse(BaseModel):
    current_version_id: str
    target_version_id: str
    skill_id: str
    current_version_number: int
    target_version_number: int
    current_status: str
    target_status: str
    is_executable: bool
    blocking_reasons: list[str]
    warnings: list[str]
    impact_summary: str
    step_delta: int


class RollbackExecuteRequest(BaseModel):
    actor: str = "system"
    reason: str = ""


class RollbackResultResponse(BaseModel):
    skill_id: str
    rolled_back_version_id: str
    rolled_back_version_number: int
    reactivated_version_id: str
    reactivated_version_number: int
    actor: str
    reason: str


class LifecycleEventEntryResponse(BaseModel):
    event_id: str
    version_id: str
    skill_id: str
    event_type: str
    from_status: str
    to_status: str
    actor: str
    reason: str
    created_at: str


class LifecycleAuditResponse(BaseModel):
    version_id: str
    skill_id: str
    current_status: str
    version_number: int
    events: list[LifecycleEventEntryResponse]
