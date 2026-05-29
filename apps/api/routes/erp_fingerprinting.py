"""Sprint 56 — ERP Fingerprinting Plan API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from erpguard.db.session import SessionLocal  # noqa: E402
from erpguard.product.erp_fingerprinting_plan import (  # noqa: E402
    ERPFingerprintingPlanService,
    FingerprintingPlanInput,
)
from erpguard.product.erp_fingerprinting_audit import ERPFingerprintingAuditService  # noqa: E402
from apps.api.schemas.erp_fingerprinting import (  # noqa: E402
    FingerprintingPlanRequest,
    FingerprintingPlanResponse,
    FingerprintingPlanDetailResponse,
    FingerprintingPlanListResponse,
    FingerprintingPlanListItem,
    FingerprintingAuditResponse,
    FingerprintingAuditEventResponse,
)

router = APIRouter(
    prefix="/v1/operator-console/connectors", tags=["ERP Fingerprinting"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/setup-session/{session_id}/fingerprinting-plan",
    response_model=FingerprintingPlanResponse,
)
def create_fingerprinting_plan(
    session_id: str,
    request: FingerprintingPlanRequest,
    db: Session = Depends(get_db),
):
    """Create a plan-only fingerprinting artifact from setup session + credential ref."""
    service = ERPFingerprintingPlanService(db)
    plan_input = FingerprintingPlanInput(
        setup_session_id=session_id,
        credential_ref=request.credential_ref,
        created_by=request.created_by,
        manual_hint=request.manual_hint,
    )
    result = service.create_plan(plan_input)
    return FingerprintingPlanResponse(**result.__dict__)


@router.get(
    "/fingerprinting-plan/{fingerprint_plan_id}",
    response_model=FingerprintingPlanDetailResponse,
)
def get_fingerprinting_plan(
    fingerprint_plan_id: str,
    db: Session = Depends(get_db),
):
    """Retrieve a fingerprinting plan by ID."""
    service = ERPFingerprintingPlanService(db)
    result = service.get_plan(fingerprint_plan_id)
    if result is None:
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=404, content={"detail": "Fingerprinting plan not found"}
        )
    return FingerprintingPlanDetailResponse(**result)


@router.get(
    "/fingerprinting-plans",
    response_model=FingerprintingPlanListResponse,
)
def list_fingerprinting_plans(
    db: Session = Depends(get_db),
):
    """List all fingerprinting plans."""
    service = ERPFingerprintingPlanService(db)
    plans = service.list_plans()
    return FingerprintingPlanListResponse(
        plans=[FingerprintingPlanListItem(**p) for p in plans]
    )


@router.get(
    "/fingerprinting-audit",
    response_model=FingerprintingAuditResponse,
)
def get_fingerprinting_audit(
    db: Session = Depends(get_db),
):
    """Retrieve fingerprinting audit trail."""
    service = ERPFingerprintingAuditService(db)
    result = service.get_audit()
    return FingerprintingAuditResponse(
        events=[FingerprintingAuditEventResponse(**e) for e in result.events]
    )
