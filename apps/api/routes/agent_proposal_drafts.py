from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.agent_proposal_drafts import (
    CreateDraftResponse,
    DraftLinkResponse,
    DraftPreviewResponse,
    SourceProposalResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_draft_service import AgentDraftService


router = APIRouter(prefix="/v1/agent-builder/advisory", tags=["agent-proposal-drafts"])


@router.post("/proposals/{proposal_id}/draft-preview", response_model=DraftPreviewResponse)
def draft_preview(proposal_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            result = AgentDraftService(session).preview(proposal_id)
            return result.model_dump()
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


@router.post("/proposals/{proposal_id}/create-draft", response_model=CreateDraftResponse)
def create_draft(proposal_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return AgentDraftService(session).create_draft(proposal_id)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
        except ValueError as exc:
            return JSONResponse(
                status_code=422,
                content={"error": {"code": "draft_creation_blocked", "message": str(exc)}},
            )
    finally:
        session.close()


@router.get("/proposals/{proposal_id}/draft-link", response_model=DraftLinkResponse)
def get_draft_link(proposal_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return AgentDraftService(session).get_draft_link(proposal_id)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


@router.get("/drafts/{draft_id}/source-proposal", response_model=SourceProposalResponse)
def get_source_proposal(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return AgentDraftService(session).get_source_proposal(draft_id)
        except ObjectNotFoundError as exc:
            return _not_found(str(exc))
    finally:
        session.close()


def _not_found(message: str):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "advisory_draft_not_found", "message": message}},
    )
