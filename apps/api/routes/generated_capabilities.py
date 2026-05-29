"""Sprint 58 - generated capabilities API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.generated_capabilities import (
    GeneratedCapabilityAuditEventResponse,
    GeneratedCapabilityAuditResponse,
    GeneratedCapabilityRequest,
    GeneratedCapabilitySetListItem,
    GeneratedCapabilitySetListResponse,
    GeneratedCapabilitySetResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.generated_capability_audit import (
    GeneratedCapabilityAuditService,
)
from erpguard.product.generated_capability_set import (
    GeneratedCapabilityInput,
    GeneratedCapabilitySetService,
)

router = APIRouter(
    prefix="/v1/operator-console/connectors", tags=["Generated Capabilities"]
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/safe-discovery-plan/{discovery_plan_id}/generated-capabilities",
    response_model=GeneratedCapabilitySetResponse,
)
def generate_capabilities_endpoint(
    discovery_plan_id: str,
    request: GeneratedCapabilityRequest,
    db: Session = Depends(get_db),
):
    service = GeneratedCapabilitySetService(db)
    result = service.generate(
        GeneratedCapabilityInput(
            discovery_plan_id=discovery_plan_id,
            created_by=request.created_by,
        )
    )
    return GeneratedCapabilitySetResponse(**result.__dict__)


@router.get(
    "/generated-capabilities/{capability_set_id}",
    response_model=GeneratedCapabilitySetResponse,
)
def get_generated_capabilities_endpoint(
    capability_set_id: str,
    db: Session = Depends(get_db),
):
    service = GeneratedCapabilitySetService(db)
    result = service.get(capability_set_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Generated capability set not found"}
        )
    return GeneratedCapabilitySetResponse(**result)


@router.get(
    "/generated-capability-sets",
    response_model=GeneratedCapabilitySetListResponse,
)
def list_generated_capability_sets_endpoint(db: Session = Depends(get_db)):
    service = GeneratedCapabilitySetService(db)
    sets = service.list()
    return GeneratedCapabilitySetListResponse(
        capability_sets=[GeneratedCapabilitySetListItem(**item) for item in sets]
    )


@router.get(
    "/generated-capability-audit",
    response_model=GeneratedCapabilityAuditResponse,
)
def get_generated_capability_audit_endpoint(db: Session = Depends(get_db)):
    service = GeneratedCapabilityAuditService(db)
    audit = service.get_audit()
    return GeneratedCapabilityAuditResponse(
        events=[GeneratedCapabilityAuditEventResponse(**event) for event in audit.events]
    )
