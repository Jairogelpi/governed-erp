from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.live_read_sandbox import (
    ConnectionContextResponse,
    LiveReadEvidenceResponse,
    LiveReadExecutionRequestBody,
    LiveReadExecutionRequestResponse,
    LiveReadPolicyResponse,
    LiveReadRunResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.connection_context import ConnectionContextService
from erpguard.product.live_read_evidence import LiveReadEvidenceService
from erpguard.product.live_read_policy import LiveReadPolicyService
from erpguard.product.live_read_request import LiveReadRequestService
from erpguard.product.live_read_runtime import LiveReadRuntimeService

router = APIRouter(prefix="/v1/product", tags=["live-read-sandbox"])


@router.get("/skills/{skill_id}/connection-context", response_model=ConnectionContextResponse)
def get_connection_context(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            ctx = ConnectionContextService(session).resolve(skill_id)
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        return ctx.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/live-read-policy", response_model=LiveReadPolicyResponse)
def check_live_read_policy(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        result = LiveReadPolicyService(session).check(skill_id)
        return result.to_dict()
    finally:
        session.close()


@router.post("/skills/{skill_id}/live-read-execution-request", response_model=LiveReadExecutionRequestResponse)
def create_live_read_execution_request(skill_id: str, body: LiveReadExecutionRequestBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            req, is_duplicate = LiveReadRequestService(session).create(
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


@router.get("/skills/{skill_id}/live-read-execution-requests", response_model=list[LiveReadExecutionRequestResponse])
def list_live_read_execution_requests(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        reqs = LiveReadRequestService(session).list_for_skill(skill_id)
        return [r.model_dump() for r in reqs]
    finally:
        session.close()


@router.get("/skills/{skill_id}/live-read-execution-requests/{request_id}", response_model=LiveReadExecutionRequestResponse)
def get_live_read_execution_request(skill_id: str, request_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            req = LiveReadRequestService(session).get(request_id)
        except ObjectNotFoundError as exc:
            return _not_found("live_read_request_not_found", str(exc))
        return req.model_dump()
    finally:
        session.close()


@router.post("/execution-requests/{execution_request_id}/run-live-read", response_model=LiveReadRunResponse)
def run_live_read(execution_request_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            run = LiveReadRuntimeService(session).execute(execution_request_id)
        except ObjectNotFoundError as exc:
            return _not_found("live_read_request_not_found", str(exc))
        except ValueError as exc:
            return _controlled_error("live_read_policy_blocked", str(exc), status_code=422)
        return run.model_dump()
    finally:
        session.close()


@router.get("/live-read-runs/{run_id}", response_model=LiveReadRunResponse)
def get_live_read_run(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            run = LiveReadRuntimeService(session).get(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("live_read_run_not_found", str(exc))
        return run.model_dump()
    finally:
        session.close()


@router.get("/live-read-runs/{run_id}/live-evidence", response_model=list[LiveReadEvidenceResponse])
def list_live_evidence(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        evidence = LiveReadEvidenceService(session).list_for_run(run_id)
        return [e.model_dump() for e in evidence]
    finally:
        session.close()


@router.get("/live-read-runs/{run_id}/blocked-write-evidence", response_model=list[dict])
def list_blocked_write_evidence_for_live_run(run_id: str):
    from erpguard.db.repositories import list_blocked_write_evidence_for_run
    init_db()
    session = SessionLocal()
    try:
        rows = list_blocked_write_evidence_for_run(session, run_id)
        return [
            {
                "evidence_id": r.id,
                "execution_run_id": r.execution_run_id,
                "execution_request_id": r.execution_request_id,
                "skill_id": r.skill_id,
                "attempted_model": r.attempted_model,
                "attempted_method": r.attempted_method,
                "blocked_reason": r.blocked_reason,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


def _controlled_error(code: str, message: str, status_code: int = 400):
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
