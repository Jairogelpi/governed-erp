"""Sprint 78 - Odoo read evidence pack API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.odoo_read_evidence import (
    OdooReadEvidenceAuditEventResponse,
    OdooReadEvidenceAuditResponse,
    OdooReadEvidencePackListResponse,
    OdooReadEvidencePackRequest,
    OdooReadEvidencePackResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.odoo_read_evidence_pack import (
    OdooReadEvidenceAuditService,
    OdooReadEvidencePackInput,
    OdooReadEvidencePackService,
)

router = APIRouter(
    prefix="/v1/operator-console/connectors",
    tags=["Odoo Read Evidence Packs"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/odoo-read-mapping/{read_mapping_id}/evidence-pack",
    response_model=OdooReadEvidencePackResponse,
)
def create_odoo_read_evidence_pack_endpoint(
    read_mapping_id: str,
    request: OdooReadEvidencePackRequest,
    db: Session = Depends(get_db),
):
    result = OdooReadEvidencePackService(db).create_pack(
        OdooReadEvidencePackInput(
            read_mapping_id=read_mapping_id,
            created_by=request.created_by,
        )
    )
    return OdooReadEvidencePackResponse(**result.__dict__)


@router.get(
    "/odoo-read-evidence-pack/{evidence_pack_id}",
    response_model=OdooReadEvidencePackResponse,
)
def get_odoo_read_evidence_pack_endpoint(
    evidence_pack_id: str,
    db: Session = Depends(get_db),
):
    result = OdooReadEvidencePackService(db).get_pack(evidence_pack_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Odoo read evidence pack not found"}
        )
    return OdooReadEvidencePackResponse(**result)


@router.get(
    "/odoo-read-evidence-packs",
    response_model=OdooReadEvidencePackListResponse,
)
def list_odoo_read_evidence_packs_endpoint(db: Session = Depends(get_db)):
    result = OdooReadEvidencePackService(db).list_packs()
    return OdooReadEvidencePackListResponse(
        evidence_packs=[OdooReadEvidencePackResponse(**item) for item in result]
    )


@router.get(
    "/odoo-read-evidence-audit",
    response_model=OdooReadEvidenceAuditResponse,
)
def get_odoo_read_evidence_audit_endpoint(db: Session = Depends(get_db)):
    result = OdooReadEvidenceAuditService(db).get_audit()
    return OdooReadEvidenceAuditResponse(
        events=[OdooReadEvidenceAuditEventResponse(**event) for event in result.events]
    )
