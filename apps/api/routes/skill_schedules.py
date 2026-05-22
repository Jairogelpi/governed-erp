from __future__ import annotations

from datetime import datetime
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.skill_schedules import (
    CreateScheduleRequest,
    QueueEntryResponse,
    ScheduleDetailResponse,
    ScheduleEventEntryResponse,
    ScheduleEventsResponse,
    ScheduleQueueResponse,
    TickDispatchResponse,
    TickFailureResponse,
    TickReportResponse,
    TickRequest,
    TickSkipResponse,
    TransitionRequest,
)
from erpguard.product.skill_schedule import SkillScheduleService
from erpguard.product.skill_schedule_audit import SkillScheduleAuditService
from erpguard.product.skill_schedule_tick import SkillScheduleTickService
from erpguard.product.skill_run_queue import SkillRunQueueService


router = APIRouter(prefix="/v1/skills", tags=["skill-schedules"])

_schedules = SkillScheduleService()
_audit = SkillScheduleAuditService()
_tick = SkillScheduleTickService()
_queue = SkillRunQueueService()


def _to_detail_response(d) -> ScheduleDetailResponse:
    return ScheduleDetailResponse(**d.__dict__)


@router.post("/schedules/tick", response_model=TickReportResponse)
def schedules_tick(request: TickRequest | None = None):
    now = None
    if request and request.now:
        try:
            now = datetime.fromisoformat(request.now)
        except ValueError:
            return JSONResponse(status_code=400, content={"error": {"code": "invalid_now", "detail": "now must be ISO-8601"}})
    report = _tick.tick(now=now)
    return TickReportResponse(
        now=report.now,
        due_count=report.due_count,
        dispatched=[TickDispatchResponse(**d.__dict__) for d in report.dispatched],
        skipped=[TickSkipResponse(**s.__dict__) for s in report.skipped],
        failed=[TickFailureResponse(**f.__dict__) for f in report.failed],
    )


@router.post("/versions/{version_id}/schedules", response_model=ScheduleDetailResponse)
def create_schedule(version_id: str, request: CreateScheduleRequest):
    try:
        result = _schedules.create_schedule(
            version_id=version_id,
            name=request.name,
            interval_seconds=request.interval_seconds,
            target_base_url=request.target_base_url,
            min_interval_seconds=request.min_interval_seconds,
            dedup_window_seconds=request.dedup_window_seconds,
            inputs=request.inputs,
            created_by=request.created_by,
        )
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "schedule_creation_error", "detail": str(exc)}})
    return _to_detail_response(result)


@router.get("/schedules/{schedule_id}", response_model=ScheduleDetailResponse)
def get_schedule(schedule_id: str):
    result = _schedules.get_schedule(schedule_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "schedule_not_found", "schedule_id": schedule_id}})
    return _to_detail_response(result)


@router.post("/schedules/{schedule_id}/activate", response_model=ScheduleDetailResponse)
def activate_schedule(schedule_id: str, request: TransitionRequest):
    try:
        result = _schedules.activate(schedule_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "transition_error", "detail": str(exc)}})
    return _to_detail_response(result)


@router.post("/schedules/{schedule_id}/pause", response_model=ScheduleDetailResponse)
def pause_schedule(schedule_id: str, request: TransitionRequest):
    try:
        result = _schedules.pause(schedule_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "transition_error", "detail": str(exc)}})
    return _to_detail_response(result)


@router.post("/schedules/{schedule_id}/resume", response_model=ScheduleDetailResponse)
def resume_schedule(schedule_id: str, request: TransitionRequest):
    try:
        result = _schedules.resume(schedule_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "transition_error", "detail": str(exc)}})
    return _to_detail_response(result)


@router.post("/schedules/{schedule_id}/disable", response_model=ScheduleDetailResponse)
def disable_schedule(schedule_id: str, request: TransitionRequest):
    try:
        result = _schedules.disable(schedule_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "transition_error", "detail": str(exc)}})
    return _to_detail_response(result)


@router.get("/schedules/{schedule_id}/events", response_model=ScheduleEventsResponse)
def get_schedule_events(schedule_id: str):
    events = _audit.list_events(schedule_id)
    if events is None:
        return JSONResponse(status_code=404, content={"error": {"code": "schedule_not_found", "schedule_id": schedule_id}})
    return ScheduleEventsResponse(
        schedule_id=schedule_id,
        event_count=len(events),
        events=[ScheduleEventEntryResponse(**e.__dict__) for e in events],
    )


@router.get("/schedules/{schedule_id}/queue", response_model=ScheduleQueueResponse)
def get_schedule_queue(schedule_id: str):
    schedule = _schedules.get_schedule(schedule_id)
    if schedule is None:
        return JSONResponse(status_code=404, content={"error": {"code": "schedule_not_found", "schedule_id": schedule_id}})
    entries = _queue.list_for_schedule(schedule_id)
    return ScheduleQueueResponse(
        schedule_id=schedule_id,
        queue_entry_count=len(entries),
        entries=[QueueEntryResponse(**e.__dict__) for e in entries],
    )


@router.get("/{skill_id}/schedules", response_model=list[ScheduleDetailResponse])
def list_schedules_for_skill(skill_id: str):
    return [_to_detail_response(s) for s in _schedules.list_schedules_for_skill(skill_id)]
