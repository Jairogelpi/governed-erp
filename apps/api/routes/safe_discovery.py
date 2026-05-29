"""Sprint 57 - Safe Discovery Plan API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.safe_discovery import (
    SafeDiscoveryAuditEventResponse,
    SafeDiscoveryAuditResponse,
    SafeDiscoveryPlanListItem,
    SafeDiscoveryPlanListResponse,
    SafeDiscoveryPlanRequest,
    SafeDiscoveryPlanResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.safe_discovery_audit import SafeDiscoveryAuditService
from erpguard.product.safe_discovery_plan import (
    SafeDiscoveryPlanInput,
    SafeDiscoveryPlanService,
)

router = APIRouter(
    prefix="/v1/operator-console/connectors", tags=["Safe Discovery"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/fingerprinting-plan/{fingerprint_plan_id}/safe-discovery-plan",
    response_model=SafeDiscoveryPlanResponse,
)
def create_safe_discovery_plan_endpoint(
    fingerprint_plan_id: str,
    request: SafeDiscoveryPlanRequest,
    db: Session = Depends(get_db),
):
    service = SafeDiscoveryPlanService(db)
    result = service.create_plan(
        SafeDiscoveryPlanInput(
            fingerprint_plan_id=fingerprint_plan_id,
            selected_adapter_type=request.selected_adapter_type,
            created_by=request.created_by,
        )
    )
    return SafeDiscoveryPlanResponse(**result.__dict__)


@router.get(
    "/safe-discovery-plan/{discovery_plan_id}",
    response_model=SafeDiscoveryPlanResponse,
)
def get_safe_discovery_plan_endpoint(
    discovery_plan_id: str,
    db: Session = Depends(get_db),
):
    service = SafeDiscoveryPlanService(db)
    result = service.get_plan(discovery_plan_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Safe discovery plan not found"}
        )
    return SafeDiscoveryPlanResponse(**result)


@router.get(
    "/safe-discovery-plans",
    response_model=SafeDiscoveryPlanListResponse,
)
def list_safe_discovery_plans_endpoint(db: Session = Depends(get_db)):
    service = SafeDiscoveryPlanService(db)
    plans = service.list_plans()
    return SafeDiscoveryPlanListResponse(
        plans=[SafeDiscoveryPlanListItem(**plan) for plan in plans]
    )


@router.get(
    "/safe-discovery-audit",
    response_model=SafeDiscoveryAuditResponse,
)
def get_safe_discovery_audit_endpoint(db: Session = Depends(get_db)):
    service = SafeDiscoveryAuditService(db)
    audit = service.get_audit()
    return SafeDiscoveryAuditResponse(
        events=[SafeDiscoveryAuditEventResponse(**event) for event in audit.events]
    )
