from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.active_skill_runner import (
    ManualRunRequest,
    ManualRunResponse,
    RunEventEntryResponse,
    RunEventsResponse,
    RunReportResponse,
    RunSummaryResponse,
)
from erpguard.product.active_skill_runner import ActiveSkillRunnerService
from erpguard.product.active_skill_run_history import ActiveSkillRunHistoryService
from erpguard.product.active_skill_run_report import ActiveSkillRunReportService


router = APIRouter(prefix="/v1/skills", tags=["active-skill-runner"])

_runner = ActiveSkillRunnerService()
_history = ActiveSkillRunHistoryService()
_report = ActiveSkillRunReportService()


@router.post("/versions/{version_id}/manual-run", response_model=ManualRunResponse)
def manual_run(version_id: str, request: ManualRunRequest):
    try:
        result = _runner.run(
            version_id=version_id,
            target_base_url=request.target_base_url,
            actor=request.actor,
            inputs=request.inputs,
        )
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": {"code": "version_not_found", "detail": str(exc)}})
    return ManualRunResponse(
        run_id=result.run_id,
        version_id=result.version_id,
        skill_id=result.skill_id,
        status=result.status,
        replay_run_id=result.replay_run_id,
        steps_passed=result.steps_passed,
        steps_failed=result.steps_failed,
        steps_verification_failed=result.steps_verification_failed,
        summary=result.summary,
        actor=result.actor,
        target_base_url=result.target_base_url,
        inputs=result.inputs,
        gate_checks=result.gate_checks,
        input_validation_checks=result.input_validation_checks,
        finished_at=result.finished_at,
    )


@router.get("/runs/{run_id}", response_model=RunSummaryResponse)
def get_run(run_id: str):
    result = _history.get_run(run_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "run_not_found", "run_id": run_id}})
    return RunSummaryResponse(**result.__dict__)


@router.get("/runs/{run_id}/events", response_model=RunEventsResponse)
def get_run_events(run_id: str):
    events = _history.list_run_events(run_id)
    if events is None:
        return JSONResponse(status_code=404, content={"error": {"code": "run_not_found", "run_id": run_id}})
    return RunEventsResponse(
        run_id=run_id,
        event_count=len(events),
        events=[RunEventEntryResponse(**e.__dict__) for e in events],
    )


@router.get("/runs/{run_id}/report", response_model=RunReportResponse)
def get_run_report(run_id: str):
    result = _report.get_report(run_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "run_not_found", "run_id": run_id}})
    return RunReportResponse(**result.__dict__)


@router.get("/{skill_id}/active-runs", response_model=list[RunSummaryResponse])
def list_runs_for_skill(skill_id: str):
    runs = _history.list_runs_for_skill(skill_id)
    return [RunSummaryResponse(**r.__dict__) for r in runs]
