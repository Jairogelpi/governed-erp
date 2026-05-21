from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.r2_write_pilot import (
    R2WritePilotEvidenceResponse,
    R2WritePilotPolicyCheckResponse,
    R2WritePilotRequestBody,
    R2WritePilotRequestResponse,
    R2WritePilotRunResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.r2_write_executor import R2WritePilotExecutorService
from erpguard.product.r2_write_policy import R2WritePilotPolicyService
from erpguard.product.r2_write_request import R2WritePilotRequestService

router = APIRouter(prefix="/v1/product", tags=["r2-write-pilot"])


@router.post("/skills/{skill_id}/r2-write-pilot/request", response_model=R2WritePilotRequestResponse)
def create_r2_write_pilot_request(skill_id: str, body: R2WritePilotRequestBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            model, is_dup = R2WritePilotRequestService(session).create(
                skill_id=skill_id,
                requested_by=body.requested_by,
                approver_1=body.approver_1,
                approver_2=body.approver_2,
                target_record_id=body.target_record_id,
                vals=body.vals,
                environment=body.environment,
            )
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"error": {"code": "invalid_request", "message": str(exc)}})
        result = model.model_dump()
        result["_idempotent_duplicate"] = is_dup
        return result
    finally:
        session.close()


@router.post("/r2-write-pilot/requests/{request_id}/policy-check", response_model=R2WritePilotPolicyCheckResponse)
def check_r2_write_pilot_policy(request_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            req = R2WritePilotRequestService(session).get(request_id)
        except ObjectNotFoundError as exc:
            return _not_found("request_not_found", str(exc))
        result = R2WritePilotPolicyService(session).check(
            skill_id=req.skill_id,
            request_id=request_id,
            target_model=req.target_model,
            target_fields=req.target_fields,
            environment=req.environment,
            approver_1_id=req.approver_1.get("id", ""),
            approver_2_id=req.approver_2.get("id", ""),
        )
        return result.model_dump()
    finally:
        session.close()


@router.post("/r2-write-pilot/requests/{request_id}/execute", response_model=R2WritePilotRunResponse)
def execute_r2_write_pilot(request_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            run = R2WritePilotExecutorService(session).execute(request_id)
        except ObjectNotFoundError as exc:
            return _not_found("request_not_found", str(exc))
        return run.model_dump()
    finally:
        session.close()


@router.get("/r2-write-pilot/runs/{run_id}", response_model=R2WritePilotRunResponse)
def get_r2_write_pilot_run(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            run = R2WritePilotExecutorService(session).get(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("run_not_found", str(exc))
        return run.model_dump()
    finally:
        session.close()


@router.get("/r2-write-pilot/runs/{run_id}/evidence", response_model=list[R2WritePilotEvidenceResponse])
def get_r2_write_pilot_evidence(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        evidence = R2WritePilotExecutorService(session).get_evidence(run_id)
        return [e.model_dump() for e in evidence]
    finally:
        session.close()


@router.get("/skills/{skill_id}/r2-write-pilot/history", response_model=list[R2WritePilotRequestResponse])
def get_r2_write_pilot_history(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        requests = R2WritePilotRequestService(session).list_for_skill(skill_id)
        return [r.model_dump() for r in requests]
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})
