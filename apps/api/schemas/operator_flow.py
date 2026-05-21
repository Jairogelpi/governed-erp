from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class CreateOperatorSessionResponse(BaseModel):
    session_id: str
    tenant_id: str | None = None
    connection_id: str | None = None
    current_step: str
    status: str
    known_ids: dict[str, Any] = {}
    created_at: str | None = None
    updated_at: str | None = None


class OperatorSessionResponse(BaseModel):
    session_id: str
    tenant_id: str | None = None
    connection_id: str | None = None
    current_step: str
    status: str
    known_ids: dict[str, Any] = {}
    created_at: str | None = None
    updated_at: str | None = None


class SelectTenantBody(BaseModel):
    tenant_id: str


class SelectConnectionBody(BaseModel):
    connection_id: str


class SelectOpportunityBody(BaseModel):
    opportunity_id: str | None = None


class RunNextResponse(BaseModel):
    session_id: str
    tenant_id: str | None = None
    connection_id: str | None = None
    current_step: str
    status: str
    known_ids: dict[str, Any] = {}
    step_status: str = "ok"
    message: str = ""


class RunSafeReadonlyPathResponse(BaseModel):
    session_id: str
    tenant_id: str | None = None
    connection_id: str | None = None
    current_step: str
    status: str
    known_ids: dict[str, Any] = {}
    steps_executed: list[str] = []
    errors: list[str] = []
    message: str = ""


class OperatorTimelineEventResponse(BaseModel):
    event_id: str
    step: str
    status: str
    detail: dict[str, Any] = {}
    created_at: str | None = None


class OperatorTimelineResponse(BaseModel):
    session_id: str
    current_step: str
    status: str
    events: list[OperatorTimelineEventResponse] = []
    steps_completed: list[str] = []
    steps_errored: list[str] = []


class OperatorSummaryResponse(BaseModel):
    session_id: str
    status: str
    current_step: str
    progress_pct: int
    steps_completed: int
    steps_total: int
    known_ids: dict[str, Any] = {}
    completed_steps: list[str] = []
    errored_steps: list[str] = []
    safety_invariants: dict[str, Any] = {}
