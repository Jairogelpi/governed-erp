from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.approval_workflow import (
    ActivationGateResponse,
    ApprovalDecisionBody,
    ApprovalDecisionResponse,
    ApprovalRequestBody,
    ApprovalRequestResponse,
    GovernanceSummaryResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.activation_gate import ActivationGateService
from erpguard.product.approval_decision import ApprovalDecisionService
from erpguard.product.approval_request import ApprovalRequestService
from erpguard.product.governance_summary import GovernanceSummaryService

router = APIRouter(prefix="/v1/product", tags=["approval-workflow"])


@router.post("/skills/{skill_id}/approval-request", response_model=ApprovalRequestResponse)
def create_approval_request(skill_id: str, body: ApprovalRequestBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            req = ApprovalRequestService(session).create(
                skill_id=skill_id,
                requested_by=body.requested_by,
                reason=body.reason,
                context=body.context,
            )
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        return req.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/approval-request", response_model=ApprovalRequestResponse)
def get_approval_request(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        req = ApprovalRequestService(session).get_latest(skill_id)
        if req is None:
            return _not_found("approval_request_not_found", f"No approval request found for skill '{skill_id}'.")
        return req.model_dump()
    finally:
        session.close()


@router.post("/skills/{skill_id}/approval-decision", response_model=ApprovalDecisionResponse)
def make_approval_decision(skill_id: str, body: ApprovalDecisionBody):
    init_db()
    session = SessionLocal()
    try:
        try:
            decision = ApprovalDecisionService(session).decide(
                skill_id=skill_id,
                decided_by=body.decided_by,
                decision=body.decision,
                reason=body.reason,
            )
        except ObjectNotFoundError as exc:
            return _not_found("approval_request_not_found", str(exc))
        except ValueError as exc:
            return _controlled_error("approval_decision_invalid", str(exc), status_code=422)
        return decision.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/approval-history", response_model=list[ApprovalDecisionResponse])
def get_approval_history(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        history = ApprovalDecisionService(session).list_history(skill_id)
        return [d.model_dump() for d in history]
    finally:
        session.close()


@router.post("/skills/{skill_id}/activation-gate", response_model=ActivationGateResponse)
def run_activation_gate(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            gate = ActivationGateService(session).evaluate(skill_id)
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        return gate.model_dump()
    finally:
        session.close()


@router.get("/skills/{skill_id}/governance-summary", response_model=GovernanceSummaryResponse)
def get_governance_summary(skill_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            summary = GovernanceSummaryService(session).summarize(skill_id)
        except ObjectNotFoundError as exc:
            return _not_found("skill_not_found", str(exc))
        return summary.model_dump()
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})


def _controlled_error(code: str, message: str, status_code: int = 400):
    return JSONResponse(status_code=status_code, content={"error": {"code": code, "message": message}})
