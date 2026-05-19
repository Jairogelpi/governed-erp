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


class SkillInspectWorkflowStepResponse(BaseModel):
    id: str
    type: str
    target: str | None = None
    selector: str | None = None
    selector_template: str | None = None
    guard: str | None = None
    value: str | None = None


class SkillInspectSafetySummaryResponse(BaseModel):
    has_guards: bool
    guard_count: int
    has_write_actions: bool
    requires_llm_for_replay: bool


class SkillInspectResponse(BaseModel):
    skill_id: str
    name: str
    version_id: str
    runtime_type: str
    llm_required_for_repeated_runs: bool
    inputs: dict[str, Any] = Field(default_factory=dict)
    guards: list[str] = Field(default_factory=list)
    workflow_steps: list[SkillInspectWorkflowStepResponse] = Field(default_factory=list)
    compiled_from_recording_id: str | None = None
    safety_summary: SkillInspectSafetySummaryResponse


class SkillRunInputsRequest(BaseModel):
    order_reference: str = Field(min_length=1)


class SkillRunRequest(BaseModel):
    inputs: SkillRunInputsRequest


class SkillRunTokenEconomics(BaseModel):
    creation_token_cost_estimate: int
    repeated_execution_token_cost: int
    estimated_tokens_saved: int


class SkillRunResponse(BaseModel):
    skill_run_id: str
    skill_id: str
    status: str
    decision: str
    output: dict[str, Any]
    token_economics: SkillRunTokenEconomics


class SkillRunStepResponse(BaseModel):
    id: str
    step_id: str
    step_type: str
    status: str
    url: str | None = None
    selector: str | None = None
    input_json: dict[str, Any] | None = None
    output_json: dict[str, Any] | None = None
    error_text: str | None = None
    created_at: str | None = None


class SkillRunDetailResponse(SkillRunResponse):
    skill_version_id: str
    input: dict[str, Any] | None = None
    error_text: str | None = None
    created_at: str
    finished_at: str | None = None
    steps: list[SkillRunStepResponse] = Field(default_factory=list)


class SkillRuntimeRequest(BaseModel):
    base_url: str


class SkillUIRunRequest(BaseModel):
    inputs: SkillRunInputsRequest
    runtime: SkillRuntimeRequest


class SkillUIRunResponse(SkillRunResponse):
    visited_urls: list[str] = Field(default_factory=list)
    selectors_used: list[str] = Field(default_factory=list)
    steps: list[SkillRunStepResponse] = Field(default_factory=list)
    no_llm_used: bool = True


class SkillRunSummaryResponse(BaseModel):
    skill_run_id: str
    skill_version_id: str
    status: str
    decision: str | None = None
    created_at: str
    finished_at: str | None = None
    input: dict[str, Any] | None = None
    output_summary: dict[str, Any] = Field(default_factory=dict)
    estimated_tokens_saved: int | None = None


class SkillRunListResponse(BaseModel):
    skill_id: str
    runs: list[SkillRunSummaryResponse] = Field(default_factory=list)


class SkillRunTimelineStepResponse(BaseModel):
    step_id: str
    step_type: str
    status: str
    input: dict[str, Any] | None = None
    output: dict[str, Any] | None = None
    error: str | None = None


class SkillRunTimelineProofResponse(BaseModel):
    has_guard_step: bool
    has_result_step: bool
    decision_is_auditable: bool
    llm_replay_not_required: bool


class SkillRunTimelineResponse(BaseModel):
    skill_id: str
    skill_run_id: str
    status: str
    decision: str | None = None
    timeline: list[SkillRunTimelineStepResponse] = Field(default_factory=list)
    proof: SkillRunTimelineProofResponse


class SkillApprovalGateRequest(BaseModel):
    inputs: SkillRunInputsRequest
    requested_action: str = Field(min_length=1)


class SkillApprovalGateStepResponse(BaseModel):
    id: str
    type: str
    description: str


class SkillApprovalGatePlanResponse(BaseModel):
    summary: str
    steps: list[SkillApprovalGateStepResponse] = Field(default_factory=list)


class SkillApprovalGatePreviewResponse(BaseModel):
    decision: str
    issues_count: int


class SkillApprovalGateProofResponse(BaseModel):
    critical_action_detected: bool
    approval_required: bool
    guard_checked_before_approval: bool
    real_erp_write_blocked: bool
    no_real_execution: bool


class SkillApprovalGateResponse(BaseModel):
    skill_id: str
    requested_action: str
    approval_required: bool
    risk_level: str
    status: str
    plan: SkillApprovalGatePlanResponse
    guard_preview: SkillApprovalGatePreviewResponse
    proof: SkillApprovalGateProofResponse