"""Sprint 83 - visual table/form extraction API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.visual_table_form_extraction import (
    VisualTableFormExtractionAuditEventResponse,
    VisualTableFormExtractionAuditResponse,
    VisualTableFormExtractionListResponse,
    VisualTableFormExtractionRequest,
    VisualTableFormExtractionResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.visual_table_form_extraction import (
    VisualTableFormExtractionAuditService,
    VisualTableFormExtractionInput,
    VisualTableFormExtractionService,
)

router = APIRouter(prefix="/v1/operator-console/visual-browser", tags=["Visual Table/Form Extraction"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post("/observation-snapshot/{observation_id}/table-form-extraction", response_model=VisualTableFormExtractionResponse)
def create_visual_table_form_extraction_endpoint(
    observation_id: str,
    request: VisualTableFormExtractionRequest,
    db: Session = Depends(get_db),
):
    result = VisualTableFormExtractionService(db).create_extraction(
        VisualTableFormExtractionInput(
            observation_id=observation_id,
            created_by=request.created_by,
            workflow_trace_id=request.workflow_trace_id,
            extraction_goal=request.extraction_goal,
        )
    )
    return VisualTableFormExtractionResponse(**result.__dict__)


@router.get("/table-form-extraction/{extraction_id}", response_model=VisualTableFormExtractionResponse)
def get_visual_table_form_extraction_endpoint(extraction_id: str, db: Session = Depends(get_db)):
    result = VisualTableFormExtractionService(db).get_extraction(extraction_id)
    if result is None:
        return JSONResponse(status_code=404, content={"detail": "Visual table/form extraction not found"})
    return VisualTableFormExtractionResponse(**result)


@router.get("/table-form-extractions", response_model=VisualTableFormExtractionListResponse)
def list_visual_table_form_extractions_endpoint(db: Session = Depends(get_db)):
    return VisualTableFormExtractionListResponse(
        extractions=[VisualTableFormExtractionResponse(**item) for item in VisualTableFormExtractionService(db).list_extractions()]
    )


@router.get("/table-form-extraction-audit", response_model=VisualTableFormExtractionAuditResponse)
def get_visual_table_form_extraction_audit_endpoint(db: Session = Depends(get_db)):
    result = VisualTableFormExtractionAuditService(db).get_audit()
    return VisualTableFormExtractionAuditResponse(
        events=[VisualTableFormExtractionAuditEventResponse(**event) for event in result.events]
    )
