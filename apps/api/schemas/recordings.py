from typing import Any

from pydantic import BaseModel, Field


class RecordingActorRequest(BaseModel):
    type: str
    id: str
    display_name: str


class RecordingCreateRequest(BaseModel):
    name: str
    description: str | None = None
    erp_type: str
    target_base_url: str
    actor: RecordingActorRequest


class RecordingCreateResponse(BaseModel):
    recording_id: str
    name: str
    status: str
    erp_type: str
    target_base_url: str


class RecordingEventRequest(BaseModel):
    event_type: str
    url: str | None = None
    page_title: str | None = None
    element_role: str | None = None
    element_text: str | None = None
    element_label: str | None = None
    selector: str | None = None
    input_value: str | None = None
    before_text_snapshot: str | None = None
    after_text_snapshot: str | None = None
    screenshot_path: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)


class RecordingEventResponse(BaseModel):
    event_id: str
    recording_id: str
    event_index: int
    event_type: str
    url: str | None = None
    page_title: str | None = None
    element_role: str | None = None
    element_text: str | None = None
    element_label: str | None = None
    selector: str | None = None
    input_value: str | None = None
    before_text_snapshot: str | None = None
    after_text_snapshot: str | None = None
    screenshot_path: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: str


class RecordingSummaryResponse(BaseModel):
    recording_id: str
    name: str
    description: str | None = None
    status: str
    erp_type: str
    target_base_url: str
    created_by_actor_json: dict[str, Any]
    created_at: str
    updated_at: str
    event_count: int = 0


class RecordingDetailResponse(RecordingSummaryResponse):
    events: list[RecordingEventResponse] = Field(default_factory=list)


class RecordingFinishResponse(BaseModel):
    recording_id: str
    status: str


class RecordingCompileSkillRequest(BaseModel):
    name: str
    description: str
    runtime_type: str


class RecordingCompileSkillResponse(BaseModel):
    recording_id: str
    skill_id: str
    version_id: str
    name: str
    runtime_type: str
    llm_required_for_repeated_runs: bool
    skill_package: dict[str, Any] = Field(default_factory=dict)