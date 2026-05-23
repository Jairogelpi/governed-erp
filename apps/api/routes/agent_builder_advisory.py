from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.agent_builder_advisory import (
    AdvisoryProposalResponse,
    AdvisorySessionResponse,
    CreateAdvisorySessionRequest,
    ProposalSafetyResponse,
    ProposeRequest,
    ReviseRequest,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_advisory_session import AdvisorySessionService
from erpguard.product.agent_proposal_store import ProposalStore


router = APIRouter(prefix="/v1/agent-builder/advisory", tags=["agent-builder-advisory"])


@router.post("/sessions", response_model=AdvisorySessionResponse)
def create_advisory_session(request: CreateAdvisorySessionRequest):
    init_db()
    session = SessionLocal()
    try:
        return AdvisorySessionService(session).create(request.created_by)
    finally:
        session.close()


@router.get("/sessions/{session_id}", response_model=AdvisorySessionResponse)
def get_advisory_session(session_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return AdvisorySessionService(session).get(session_id)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


@router.post("/sessions/{session_id}/propose", response_model=AdvisoryProposalResponse)
def propose(session_id: str, request: ProposeRequest):
    if not request.request_text.strip():
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "empty_request_text", "message": "request_text must not be empty."}},
        )
    init_db()
    session = SessionLocal()
    try:
        try:
            return ProposalStore(session).generate(session_id, request.request_text)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


@router.get("/proposals/{proposal_id}", response_model=AdvisoryProposalResponse)
def get_proposal(proposal_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return ProposalStore(session).get(proposal_id)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


@router.post("/proposals/{proposal_id}/revise", response_model=AdvisoryProposalResponse)
def revise_proposal(proposal_id: str, request: ReviseRequest):
    if not request.updated_request.strip():
        return JSONResponse(
            status_code=422,
            content={"error": {"code": "empty_updated_request", "message": "updated_request must not be empty."}},
        )
    init_db()
    session = SessionLocal()
    try:
        try:
            return ProposalStore(session).revise(proposal_id, request.updated_request)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


@router.get("/proposals/{proposal_id}/safety", response_model=ProposalSafetyResponse)
def proposal_safety(proposal_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return ProposalStore(session).safety_summary(proposal_id)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


def _not_found(message: str):
    return JSONResponse(status_code=404, content={"error": {"code": "advisory_not_found", "message": message}})
