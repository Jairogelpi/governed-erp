"""Sprint 80 - visual browser session shell API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.visual_browser_session import (
    VisualBrowserSessionAuditEventResponse,
    VisualBrowserSessionAuditResponse,
    VisualBrowserSessionListResponse,
    VisualBrowserSessionRequest,
    VisualBrowserSessionResponse,
    VisualBrowserSessionRevokeRequest,
)
from erpguard.db.session import SessionLocal
from erpguard.product.visual_browser_session import (
    VisualBrowserSessionAuditService,
    VisualBrowserSessionInput,
    VisualBrowserSessionService,
)

router = APIRouter(
    prefix="/v1/operator-console/visual-browser",
    tags=["Visual Browser Session"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/sessions", response_model=VisualBrowserSessionResponse)
def create_visual_browser_session_endpoint(
    request: VisualBrowserSessionRequest,
    db: Session = Depends(get_db),
):
    result = VisualBrowserSessionService(db).create_session(
        VisualBrowserSessionInput(
            created_by=request.created_by,
            target_url=request.target_url,
            intended_erp_hint=request.intended_erp_hint,
            workspace_mode=request.workspace_mode,
            credential_capture_allowed=request.credential_capture_allowed,
            automatic_clicks_allowed=request.automatic_clicks_allowed,
            action_execution_allowed=request.action_execution_allowed,
        )
    )
    return VisualBrowserSessionResponse(**result.__dict__)


@router.get("/session/{visual_session_id}", response_model=VisualBrowserSessionResponse)
def get_visual_browser_session_endpoint(
    visual_session_id: str,
    db: Session = Depends(get_db),
):
    result = VisualBrowserSessionService(db).get_session(visual_session_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Visual browser session not found"}
        )
    return VisualBrowserSessionResponse(**result)


@router.get("/sessions", response_model=VisualBrowserSessionListResponse)
def list_visual_browser_sessions_endpoint(db: Session = Depends(get_db)):
    result = VisualBrowserSessionService(db).list_sessions()
    return VisualBrowserSessionListResponse(
        sessions=[VisualBrowserSessionResponse(**item) for item in result]
    )


@router.post(
    "/session/{visual_session_id}/revoke",
    response_model=VisualBrowserSessionResponse,
)
def revoke_visual_browser_session_endpoint(
    visual_session_id: str,
    request: VisualBrowserSessionRevokeRequest,
    db: Session = Depends(get_db),
):
    result = VisualBrowserSessionService(db).revoke_session(
        visual_session_id,
        actor=request.actor,
    )
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Visual browser session not found"}
        )
    return VisualBrowserSessionResponse(**result.__dict__)


@router.get("/audit", response_model=VisualBrowserSessionAuditResponse)
def get_visual_browser_session_audit_endpoint(db: Session = Depends(get_db)):
    result = VisualBrowserSessionAuditService(db).get_audit()
    return VisualBrowserSessionAuditResponse(
        events=[VisualBrowserSessionAuditEventResponse(**event) for event in result.events]
    )
