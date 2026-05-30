"""Sprint 75 - Odoo controlled connection test API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.odoo_connection_test import (
    OdooConnectionTestAuditEventResponse,
    OdooConnectionTestAuditResponse,
    OdooConnectionTestListResponse,
    OdooConnectionTestRequest,
    OdooConnectionTestResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.odoo_connection_test import (
    OdooConnectionTestAuditService,
    OdooConnectionTestInput,
    OdooConnectionTestService,
)

router = APIRouter(
    prefix="/v1/operator-console/connectors",
    tags=["Odoo Connection Test"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/odoo-adapter-session/{adapter_session_id}/connection-test",
    response_model=OdooConnectionTestResponse,
)
def run_odoo_connection_test_endpoint(
    adapter_session_id: str,
    request: OdooConnectionTestRequest,
    db: Session = Depends(get_db),
):
    result = OdooConnectionTestService(db).run_test(
        OdooConnectionTestInput(
            adapter_session_id=adapter_session_id,
            requested_by=request.requested_by,
            allow_network_test=request.allow_network_test,
        )
    )
    return OdooConnectionTestResponse(**result.__dict__)


@router.get(
    "/odoo-connection-test/{connection_test_id}",
    response_model=OdooConnectionTestResponse,
)
def get_odoo_connection_test_endpoint(
    connection_test_id: str,
    db: Session = Depends(get_db),
):
    result = OdooConnectionTestService(db).get_test(connection_test_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Odoo connection test not found"}
        )
    return OdooConnectionTestResponse(**result)


@router.get(
    "/odoo-connection-tests",
    response_model=OdooConnectionTestListResponse,
)
def list_odoo_connection_tests_endpoint(db: Session = Depends(get_db)):
    result = OdooConnectionTestService(db).list_tests()
    return OdooConnectionTestListResponse(
        connection_tests=[OdooConnectionTestResponse(**item) for item in result]
    )


@router.get(
    "/odoo-connection-test-audit",
    response_model=OdooConnectionTestAuditResponse,
)
def get_odoo_connection_test_audit_endpoint(db: Session = Depends(get_db)):
    result = OdooConnectionTestAuditService(db).get_audit()
    return OdooConnectionTestAuditResponse(
        events=[OdooConnectionTestAuditEventResponse(**event) for event in result.events]
    )
