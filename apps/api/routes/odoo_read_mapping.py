"""Sprint 76 - Odoo read mapping API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.odoo_read_mapping import (
    OdooReadMappingAuditEventResponse,
    OdooReadMappingAuditResponse,
    OdooReadMappingListResponse,
    OdooReadMappingRequest,
    OdooReadMappingResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.odoo_read_mapping import (
    OdooReadMappingAuditService,
    OdooReadMappingInput,
    OdooReadMappingService,
)

router = APIRouter(
    prefix="/v1/operator-console/connectors",
    tags=["Odoo Read Mapping"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/odoo-connection-test/{connection_test_id}/read-mapping",
    response_model=OdooReadMappingResponse,
)
def run_odoo_read_mapping_endpoint(
    connection_test_id: str,
    request: OdooReadMappingRequest,
    db: Session = Depends(get_db),
):
    result = OdooReadMappingService(db).run_mapping(
        OdooReadMappingInput(
            connection_test_id=connection_test_id,
            requested_by=request.requested_by,
            object_type=request.object_type,
            lookup=request.lookup,
            allow_business_read=request.allow_business_read,
        )
    )
    return OdooReadMappingResponse(**result.__dict__)


@router.get(
    "/odoo-read-mapping/{read_mapping_id}",
    response_model=OdooReadMappingResponse,
)
def get_odoo_read_mapping_endpoint(read_mapping_id: str, db: Session = Depends(get_db)):
    result = OdooReadMappingService(db).get_mapping(read_mapping_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Odoo read mapping not found"}
        )
    return OdooReadMappingResponse(**result)


@router.get(
    "/odoo-read-mappings",
    response_model=OdooReadMappingListResponse,
)
def list_odoo_read_mappings_endpoint(db: Session = Depends(get_db)):
    result = OdooReadMappingService(db).list_mappings()
    return OdooReadMappingListResponse(
        read_mappings=[OdooReadMappingResponse(**item) for item in result]
    )


@router.get(
    "/odoo-read-mapping-audit",
    response_model=OdooReadMappingAuditResponse,
)
def get_odoo_read_mapping_audit_endpoint(db: Session = Depends(get_db)):
    result = OdooReadMappingAuditService(db).get_audit()
    return OdooReadMappingAuditResponse(
        events=[OdooReadMappingAuditEventResponse(**event) for event in result.events]
    )
