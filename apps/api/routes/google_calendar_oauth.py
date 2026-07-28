from __future__ import annotations

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from apps.api.schemas.google_calendar_oauth import (
    AuthorizeRequest,
    AuthorizeResponse,
    CallbackResponse,
    OAuthStatusResponse,
    RevokeRequest,
    RevokeResponse,
    ScopeVerificationResponse,
)
from sqlalchemy.orm import Session

from erpguard.db.session import SessionLocal, init_db
from erpguard.product.google_calendar_oauth import GoogleCalendarOAuthService

router = APIRouter(prefix="/v1/oauth/google-calendar", tags=["google-calendar-oauth"])


def _svc() -> tuple[GoogleCalendarOAuthService, Session]:
    init_db()
    session = SessionLocal()
    return GoogleCalendarOAuthService(session), session


@router.post("/authorize", response_model=AuthorizeResponse)
def authorize(request: AuthorizeRequest):
    svc, session = _svc()
    try:
        result = svc.build_authorization_url(
            profile_id=request.profile_id,
            redirect_uri=request.redirect_uri,
            actor=request.actor,
        )
        return result.model_dump()
    finally:
        session.close()


@router.get("/callback", response_model=CallbackResponse)
def oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State token for CSRF verification"),
):
    svc, session = _svc()
    try:
        try:
            result = svc.exchange_code(code=code, state_token=state)
        except ValueError as exc:
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "invalid_state", "message": str(exc)}},
            )
        return result.model_dump()
    finally:
        session.close()


@router.get("/status/{profile_id}", response_model=OAuthStatusResponse)
def get_auth_status(profile_id: str):
    svc, session = _svc()
    try:
        return svc.get_auth_status(profile_id).model_dump()
    finally:
        session.close()


@router.get("/verify-scope/{profile_id}", response_model=ScopeVerificationResponse)
def verify_scope(profile_id: str):
    svc, session = _svc()
    try:
        return svc.verify_scope(profile_id).model_dump()
    finally:
        session.close()


@router.post("/revoke/{profile_id}", response_model=RevokeResponse)
def revoke_token(profile_id: str, request: RevokeRequest):
    svc, session = _svc()
    try:
        return svc.revoke(profile_id=profile_id, actor=request.actor)
    finally:
        session.close()
