from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.r2_readiness import (
    R2EvidenceReviewResponse,
    R2ExecutionReportResponse,
    R2PromotionGateResponse,
    R2RollbackRehearsalResponse,
)
from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.r2_evidence_review import R2EvidenceReviewService
from erpguard.product.r2_execution_report import R2ExecutionReportService
from erpguard.product.r2_promotion_gate import R2PromotionGateService
from erpguard.product.r2_rollback_rehearsal import R2RollbackRehearsalService

router = APIRouter(prefix="/v1/product", tags=["r2-readiness"])


@router.get("/r2-write-pilot/runs/{run_id}/evidence-review", response_model=R2EvidenceReviewResponse)
def get_evidence_review(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return R2EvidenceReviewService(session).get_or_create(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("run_not_found", str(exc))
    finally:
        session.close()


@router.post("/r2-write-pilot/runs/{run_id}/rollback-rehearsal", response_model=R2RollbackRehearsalResponse)
def rehearse_rollback(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return R2RollbackRehearsalService(session).rehearse(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("run_not_found", str(exc))
    finally:
        session.close()


@router.get("/r2-write-pilot/runs/{run_id}/execution-report", response_model=R2ExecutionReportResponse)
def get_execution_report(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return R2ExecutionReportService(session).get_or_generate(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("run_not_found", str(exc))
    finally:
        session.close()


@router.post("/r2-write-pilot/runs/{run_id}/promotion-gate", response_model=R2PromotionGateResponse)
def evaluate_promotion_gate(run_id: str):
    init_db()
    session = SessionLocal()
    try:
        try:
            return R2PromotionGateService(session).evaluate(run_id)
        except ObjectNotFoundError as exc:
            return _not_found("run_not_found", str(exc))
    finally:
        session.close()


def _not_found(code: str, message: str):
    return JSONResponse(status_code=404, content={"error": {"code": code, "message": message}})
