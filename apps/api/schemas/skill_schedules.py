from __future__ import annotations

from pydantic import BaseModel, Field


class CreateScheduleRequest(BaseModel):
    name: str
    interval_seconds: int
    target_base_url: str
    min_interval_seconds: int = 60
    dedup_window_seconds: int = 30
    inputs: dict = Field(default_factory=dict)
    created_by: str = "manual_operator"


class ScheduleDetailResponse(BaseModel):
    schedule_id: str
    version_id: str
    skill_id: str
    name: str
    interval_seconds: int
    min_interval_seconds: int
    dedup_window_seconds: int
    status: str
    target_base_url: str
    inputs: dict
    next_run_at: str
    last_run_at: str
    last_run_id: str | None
    created_by: str
    created_at: str
    updated_at: str


class TransitionRequest(BaseModel):
    actor: str = "manual_operator"
    reason: str = ""


class ScheduleEventEntryResponse(BaseModel):
    event_id: str
    schedule_id: str
    event_type: str
    status: str
    detail: str
    payload: dict
    created_at: str


class ScheduleEventsResponse(BaseModel):
    schedule_id: str
    event_count: int
    events: list[ScheduleEventEntryResponse]


class QueueEntryResponse(BaseModel):
    entry_id: str
    schedule_id: str
    version_id: str
    skill_id: str
    status: str
    inputs: dict
    target_base_url: str
    run_id: str | None
    detail: str
    enqueued_at: str
    dispatched_at: str
    finished_at: str


class ScheduleQueueResponse(BaseModel):
    schedule_id: str
    queue_entry_count: int
    entries: list[QueueEntryResponse]


class TickRequest(BaseModel):
    now: str | None = None


class TickDispatchResponse(BaseModel):
    schedule_id: str
    queue_entry_id: str
    run_id: str
    run_status: str


class TickSkipResponse(BaseModel):
    schedule_id: str
    reason: str
    detail: str


class TickFailureResponse(BaseModel):
    schedule_id: str
    error: str


class TickReportResponse(BaseModel):
    now: str
    due_count: int
    dispatched: list[TickDispatchResponse]
    skipped: list[TickSkipResponse]
    failed: list[TickFailureResponse]
