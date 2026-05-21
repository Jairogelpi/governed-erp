from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.operator_flow import (
    CreateOperatorSessionResponse,
    OperatorSessionResponse,
    OperatorSummaryResponse,
    OperatorTimelineResponse,
    RunNextResponse,
    RunSafeReadonlyPathResponse,
    SelectConnectionBody,
    SelectOpportunityBody,
    SelectTenantBody,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.operator_orchestrator import OperatorOrchestrator
from erpguard.product.operator_session import OperatorSessionService
from erpguard.product.operator_summary import OperatorSummaryService
from erpguard.product.operator_timeline import OperatorTimelineService

router = APIRouter(prefix="/v1/product", tags=["operator-flow"])


@router.post("/operator-sessions", response_model=CreateOperatorSessionResponse)
def create_operator_session():
    init_db()
    session = SessionLocal()
    try:
        result = OperatorSessionService(session).create()
        return result
    finally:
        session.close()


@router.get("/operator-sessions/{session_id}", response_model=OperatorSessionResponse)
def get_operator_session(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return OperatorSessionService(session).get(session_id)
        except ObjectNotFoundError as exc:
            return _not_found("session_not_found", str(exc))
    finally:
        session.close()


@router.post("/operator-sessions/{session_id}/select-tenant", response_model=OperatorSessionResponse)
def select_tenant(session_id: str, body: SelectTenantBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            return OperatorSessionService(session).select_tenant(session_id, body.tenant_id)
        except ObjectNotFoundError as exc:
            return _not_found("session_not_found", str(exc))
    finally:
        session.close()


@router.post("/operator-sessions/{session_id}/select-connection", response_model=OperatorSessionResponse)
def select_connection(session_id: str, body: SelectConnectionBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            return OperatorSessionService(session).select_connection(session_id, body.connection_id)
        except ObjectNotFoundError as exc:
            return _not_found("session_not_found", str(exc))
    finally:
        session.close()


@router.post("/operator-sessions/{session_id}/select-opportunity", response_model=OperatorSessionResponse)
def select_opportunity(session_id: str, body: SelectOpportunityBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            if body.opportunity_id:
                result = OperatorSessionService(session).select_opportunity(session_id, body.opportunity_id)
            else:
                result = OperatorSessionService(session).get(session_id)
                opp_ids = result.get("known_ids", {}).get("opportunity_ids", [])
                if not opp_ids:
                    return JSONResponse(status_code=400, content={"error": {"code": "no_opportunities", "message": "No opportunities available. Run business analysis first."}})
                result = OperatorSessionService(session).select_opportunity(session_id, opp_ids[0])
            return result
        except ObjectNotFoundError as exc:
            return _not_found("session_not_found", str(exc))
    finally:
        session.close()


@router.post("/operator-sessions/{session_id}/run-next", response_model=RunNextResponse)
def run_next(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return OperatorOrchestrator(session).run_next(session_id)
        except ObjectNotFoundError as exc:
            return _not_found("session_not_found", str(exc))
    finally:
        session.close()


@router.post("/operator-sessions/{session_id}/run-safe-readonly-path", response_model=RunSafeReadonlyPathResponse)
def run_safe_readonly_path(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return OperatorOrchestrator(session).run_safe_readonly_path(session_id)
        except ObjectNotFoundError as exc:
            return _not_found("session_not_found", str(exc))
    finally:
        session.close()


@router.get("/operator-sessions/{session_id}/timeline", response_model=OperatorTimelineResponse)
def get_timeline(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return OperatorTimelineService(session).get_timeline(session_id)
        except ObjectNotFoundError as exc:
            return _not_found("session_not_found", str(exc))
    finally:
        session.close()


@router.get("/operator-sessions/{session_id}/summary", response_model=OperatorSummaryResponse)
def get_summary(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return OperatorSummaryService(session).summarize(session_id)
        except ObjectNotFoundError as exc:
            return _not_found("session_not_found", str(exc))
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})
