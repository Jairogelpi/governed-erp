from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.write_pilot import (
    WritePilotEvidenceResponse,
    WritePilotPolicyCheckResponse,
    WritePilotRequestBody,
    WritePilotRequestResponse,
    WritePilotRunResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.write_pilot_evidence import WritePilotEvidenceService
from erpguard.product.write_pilot_executor import WritePilotExecutorService
from erpguard.product.write_pilot_policy import WritePilotPolicyService
from erpguard.product.write_pilot_request import WritePilotRequestService

router = APIRouter(prefix="/v1/product", tags=["write-pilot"])


@router.post("/skills/{skill_id}/write-pilot/request", response_model=WritePilotRequestResponse)
def create_write_pilot_request(skill_id: str, body: WritePilotRequestBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            req, is_duplicate = WritePilotRequestService(session).create(
                skill_id=skill_id,
                requested_by=body.requested_by,
                approver_1=body.approver_1,
                approver_2=body.approver_2,
                target_res_model=body.target_res_model,
                target_res_id=body.target_res_id,
                payload=body.payload,
            )
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        data = req.model_dump()
        data["_idempotent_duplicate"] = is_duplicate
        return JSONResponse(status_code=200 if is_duplicate else 201, content=data)
    finally:
        session.close()


@router.post("/write-pilot/requests/{request_id}/policy-check", response_model=WritePilotPolicyCheckResponse)
def check_write_pilot_policy(request_id: str):
    init_db()
    session = SessionLocal()
    try:
        from erpguard.db.repositories import get_write_pilot_request
        req_row = get_write_pilot_request(session, request_id)
        if req_row is None:
            return _not_found("request_not_found", f"Write pilot request '{request_id}' not found.")
        result = WritePilotPolicyService(session).check(
            skill_id=req_row.skill_id,
            target_model=req_row.target_model,
            request_id=request_id,
        )
        d = result.model_dump()
        d["violations"] = [v.model_dump() for v in result.violations]
        return d
    finally:
        session.close()


@router.post("/write-pilot/requests/{request_id}/execute", response_model=WritePilotRunResponse)
def execute_write_pilot(request_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            run = WritePilotExecutorService(session).execute(request_id)
        except ObjectNotFoundError as exc:
            return _not_found("request_not_found", str(exc))
        return run.model_dump()
    finally:
        session.close()


@router.get("/write-pilot/runs/{run_id}", response_model=WritePilotRunResponse)
def get_write_pilot_run(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            run = WritePilotExecutorService(session).get(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("run_not_found", str(exc))
        return run.model_dump()
    finally:
        session.close()


@router.get("/write-pilot/runs/{run_id}/evidence", response_model=list[WritePilotEvidenceResponse])
def list_write_pilot_evidence(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        evidence = WritePilotEvidenceService(session).list_for_run(run_id)
        return [e.model_dump() for e in evidence]
    finally:
        session.close()


@router.get("/skills/{skill_id}/write-pilot/history", response_model=list[WritePilotRequestResponse])
def list_write_pilot_history(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        reqs = WritePilotRequestService(session).list_for_skill(skill_id)
        return [r.model_dump() for r in reqs]
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})
