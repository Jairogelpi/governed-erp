from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.agent_draft_bridge import (
    BridgeEligibilityResponse,
    ClarificationGateResponse,
    DraftBridgeAuditResponse,
    DraftBridgeReportResponse,
    DraftCompileBridgeResponse,
    DraftReviewBridgeResponse,
    DraftValidationBridgeResponse,
)
from erpguard.db.repositories import get_automation_draft
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_draft_bridge_audit import get_bridge_audit
from erpguard.product.agent_draft_bridge_eligibility import check_bridge_eligibility
from erpguard.product.agent_draft_bridge_report import get_bridge_report
from erpguard.product.agent_draft_clarification_gate import check_clarification_gate
from erpguard.product.agent_draft_compile_bridge import generate_compile_plan
from erpguard.product.agent_draft_review_bridge import bridge_to_review
from erpguard.product.agent_draft_validation_bridge import validate_agent_draft

router = APIRouter(prefix="/v1/agent-builder/advisory", tags=["agent-draft-bridge"])


def _draft_not_found(draft_id: str):
    return JSONResponse(
        status_code=404,
        content={"error": {"code": "draft_not_found", "message": f"Draft '{draft_id}' not found."}},
    )


@router.post("/drafts/{draft_id}/bridge/eligibility", response_model=BridgeEligibilityResponse)
def bridge_eligibility(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = check_bridge_eligibility(draft_id, session)
        return BridgeEligibilityResponse(**result.model_dump())
    finally:
        session.close()


@router.post("/drafts/{draft_id}/bridge/clarification-gate", response_model=ClarificationGateResponse)
def bridge_clarification_gate(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = check_clarification_gate(draft_id, session)
        return ClarificationGateResponse(**result.model_dump())
    finally:
        session.close()


@router.post("/drafts/{draft_id}/bridge/review", response_model=DraftReviewBridgeResponse)
def bridge_review(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = bridge_to_review(draft_id, session)
        return DraftReviewBridgeResponse(**result.model_dump())
    finally:
        session.close()


@router.post("/drafts/{draft_id}/bridge/validate", response_model=DraftValidationBridgeResponse)
def bridge_validate(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = validate_agent_draft(draft_id, session)
        return DraftValidationBridgeResponse(**result.model_dump())
    finally:
        session.close()


@router.post("/drafts/{draft_id}/bridge/compile-plan", response_model=DraftCompileBridgeResponse)
def bridge_compile_plan(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = generate_compile_plan(draft_id, session)
        return DraftCompileBridgeResponse(**result.model_dump())
    finally:
        session.close()


@router.get("/drafts/{draft_id}/bridge/report", response_model=DraftBridgeReportResponse)
def bridge_report(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = get_bridge_report(draft_id, session)
        return DraftBridgeReportResponse(**result.model_dump())
    finally:
        session.close()


@router.get("/drafts/{draft_id}/bridge/audit", response_model=DraftBridgeAuditResponse)
def bridge_audit(draft_id: str):
    init_db()
    session = SessionLocal()
    try:
        draft = get_automation_draft(session, draft_id)
        if draft is None:
            return _draft_not_found(draft_id)
        result = get_bridge_audit(draft_id, session)
        return DraftBridgeAuditResponse(**result.model_dump())
    finally:
        session.close()
