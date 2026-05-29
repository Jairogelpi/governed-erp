"""Sprint 74 - Odoo read-only adapter shell API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.odoo_read_only_adapter import (
    OdooReadOnlyAdapterAuditEventResponse,
    OdooReadOnlyAdapterAuditResponse,
    OdooReadOnlyAdapterSessionListResponse,
    OdooReadOnlyAdapterSessionRequest,
    OdooReadOnlyAdapterSessionResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.odoo_read_only_adapter import (
    OdooReadOnlyAdapterService,
    OdooReadOnlyConnectionIntent,
)
from erpguard.product.odoo_read_only_adapter_audit import OdooReadOnlyAdapterAuditService

router = APIRouter(
    prefix="/v1/operator-console/connectors",
    tags=["Odoo Read-Only Adapter Shell"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/read-only-activation/{activation_id}/odoo-adapter-session",
    response_model=OdooReadOnlyAdapterSessionResponse,
)
def create_odoo_adapter_session_endpoint(
    activation_id: str,
    request: OdooReadOnlyAdapterSessionRequest,
    db: Session = Depends(get_db),
):
    result = OdooReadOnlyAdapterService(db).prepare_session(
        OdooReadOnlyConnectionIntent(
            activation_id=activation_id,
            created_by=request.created_by,
        )
    )
    return OdooReadOnlyAdapterSessionResponse(**result.__dict__)


@router.get(
    "/odoo-adapter-session/{adapter_session_id}",
    response_model=OdooReadOnlyAdapterSessionResponse,
)
def get_odoo_adapter_session_endpoint(
    adapter_session_id: str,
    db: Session = Depends(get_db),
):
    result = OdooReadOnlyAdapterService(db).get_session(adapter_session_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Odoo read-only adapter session not found"}
        )
    return OdooReadOnlyAdapterSessionResponse(**result)


@router.get(
    "/odoo-adapter-sessions",
    response_model=OdooReadOnlyAdapterSessionListResponse,
)
def list_odoo_adapter_sessions_endpoint(db: Session = Depends(get_db)):
    result = OdooReadOnlyAdapterService(db).list_sessions()
    return OdooReadOnlyAdapterSessionListResponse(
        sessions=[OdooReadOnlyAdapterSessionResponse(**item) for item in result]
    )


@router.get(
    "/odoo-adapter-audit",
    response_model=OdooReadOnlyAdapterAuditResponse,
)
def get_odoo_adapter_audit_endpoint(db: Session = Depends(get_db)):
    result = OdooReadOnlyAdapterAuditService(db).get_audit()
    return OdooReadOnlyAdapterAuditResponse(
        events=[OdooReadOnlyAdapterAuditEventResponse(**event) for event in result.events]
    )
