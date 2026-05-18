from pydantic import BaseModel, Field


class DemoActorRequest(BaseModel):
    type: str
    id: str
    display_name: str


class DemoFullFlowRequest(BaseModel):
    base_url: str
    record_order_reference: str
    valid_order_reference: str
    invalid_order_reference: str
    actor: DemoActorRequest


class DemoRecordingResponse(BaseModel):
    recording_id: str
    status: str
    event_count: int


class DemoSkillResponse(BaseModel):
    skill_id: str
    version_id: str
    name: str
    llm_required_for_repeated_runs: bool


class DemoRunResponse(BaseModel):
    skill_run_id: str
    order_reference: str
    decision: str
    issues_count: int | None = None


class DemoTokenEconomicsResponse(BaseModel):
    creation_token_cost_estimate: int
    repeated_execution_token_cost: int
    estimated_tokens_saved_per_run: int
    total_estimated_tokens_saved: int


class DemoProofResponse(BaseModel):
    record_to_skill: bool = True
    deterministic_replay: bool = True
    erpguard_blocked_invalid_order: bool = True
    no_llm_used_for_repeated_runs: bool = True


class DemoFullFlowResponse(BaseModel):
    status: str
    recording: DemoRecordingResponse
    skill: DemoSkillResponse
    runs: dict[str, DemoRunResponse]
    token_economics: DemoTokenEconomicsResponse
    proof: DemoProofResponse
