from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.execution_sandbox import (
    BlockedWriteEvidenceResponse,
    ExecutionRequestBody,
    ExecutionRequestResponse,
    ExecutionRunResponse,
    ExecutionTimelineResponse,
    PolicyCheckResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.blocked_write_evidence import BlockedWriteEvidenceService
from erpguard.product.execution_gate import ExecutionGateService
from erpguard.product.execution_request import ExecutionRequestService
from erpguard.product.execution_runtime import ExecutionRuntimeService
from erpguard.product.execution_timeline import ExecutionTimelineService

router = APIRouter(prefix="/v1/product", tags=["execution-sandbox"])


@router.post("/skills/{skill_id}/execution-requests", response_model=ExecutionRequestResponse)
def create_execution_request(skill_id: str, body: ExecutionRequestBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            req, is_duplicate = ExecutionRequestService(session).create(
                skill_id=skill_id,
                requested_by=body.requested_by,
                inputs=body.inputs,
            )
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        data = req.model_dump()
        data["_idempotent_duplicate"] = is_duplicate
        return JSONResponse(status_code=200 if is_duplicate else 201, content=data)
    finally:
        session.close()


@router.get("/skills/{skill_id}/execution-requests", response_model=list[ExecutionRequestResponse])
def list_execution_requests(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        reqs = ExecutionRequestService(session).list_for_skill(skill_id)
        return [r.model_dump() for r in reqs]
    finally:
        session.close()


@router.get("/skills/{skill_id}/execution-requests/{request_id}", response_model=ExecutionRequestResponse)
def get_execution_request(skill_id: str, request_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            req = ExecutionRequestService(session).get(request_id)
        except ObjectNotFoundError as exc:
            return _not_found("execution_request_not_found", str(exc))
        return req.model_dump()
    finally:
        session.close()


@router.post("/skills/{skill_id}/execution-requests/{request_id}/run", response_model=ExecutionRunResponse)
def run_execution(skill_id: str, request_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            run = ExecutionRuntimeService(session).execute(request_id)
        except ObjectNotFoundError as exc:
            return _not_found("execution_request_not_found", str(exc))
        except ValueError as exc:
            return _controlled_error("execution_policy_blocked", str(exc), status_code=422)
        return run.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/execution-runs/{run_id}", response_model=ExecutionRunResponse)
def get_execution_run(skill_id: str, run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            run = ExecutionRuntimeService(session).get(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("execution_run_not_found", str(exc))
        return run.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/execution-runs/{run_id}/timeline", response_model=ExecutionTimelineResponse)
def get_execution_timeline(skill_id: str, run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            timeline = ExecutionTimelineService(session).get(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("execution_run_not_found", str(exc))
        return timeline.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/execution-runs/{run_id}/blocked-writes", response_model=list[BlockedWriteEvidenceResponse])
def list_blocked_writes(skill_id: str, run_id: str):
    init_db()
    session = SessionLocal()
    try:
        evidence = BlockedWriteEvidenceService(session).list_for_run(run_id)
        return [e.model_dump() for e in evidence]
    finally:
        session.close()


@router.get("/skills/{skill_id}/execution-policy", response_model=PolicyCheckResponse)
def check_execution_policy(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        result = ExecutionGateService(session).check(skill_id, "", {})
        return result.to_dict()
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


def _controlled_error(code: str, message: str, status_code: int = 400):
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
