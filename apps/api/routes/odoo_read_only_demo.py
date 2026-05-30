"""Sprint 79 - Odoo read-only demo flow API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.odoo_read_only_demo import (
    OdooReadOnlyDemoAuditEventResponse,
    OdooReadOnlyDemoAuditResponse,
    OdooReadOnlyDemoFlowListResponse,
    OdooReadOnlyDemoFlowRequest,
    OdooReadOnlyDemoFlowResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.odoo_read_only_demo_flow import (
    OdooReadOnlyDemoAuditService,
    OdooReadOnlyDemoFlowInput,
    OdooReadOnlyDemoFlowService,
)

router = APIRouter(
    prefix="/v1/operator-console/connectors",
    tags=["Odoo Read-Only Demo Flow"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/read-only-activation/{activation_id}/odoo-read-only-demo-flow",
    response_model=OdooReadOnlyDemoFlowResponse,
)
def run_odoo_read_only_demo_flow_endpoint(
    activation_id: str,
    request: OdooReadOnlyDemoFlowRequest,
    db: Session = Depends(get_db),
):
    result = OdooReadOnlyDemoFlowService(db).run_flow(
        OdooReadOnlyDemoFlowInput(
            activation_id=activation_id,
            requested_by=request.requested_by,
            object_types=request.object_types,
            allow_network_test=request.allow_network_test,
            allow_business_read=request.allow_business_read,
        )
    )
    return OdooReadOnlyDemoFlowResponse(**result.__dict__)


@router.get(
    "/odoo-read-only-demo-flow/{demo_flow_id}",
    response_model=OdooReadOnlyDemoFlowResponse,
)
def get_odoo_read_only_demo_flow_endpoint(
    demo_flow_id: str,
    db: Session = Depends(get_db),
):
    result = OdooReadOnlyDemoFlowService(db).get_flow(demo_flow_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Odoo read-only demo flow not found"}
        )
    return OdooReadOnlyDemoFlowResponse(**result)


@router.get(
    "/odoo-read-only-demo-flows",
    response_model=OdooReadOnlyDemoFlowListResponse,
)
def list_odoo_read_only_demo_flows_endpoint(db: Session = Depends(get_db)):
    result = OdooReadOnlyDemoFlowService(db).list_flows()
    return OdooReadOnlyDemoFlowListResponse(
        demo_flows=[OdooReadOnlyDemoFlowResponse(**item) for item in result]
    )


@router.get(
    "/odoo-read-only-demo-audit",
    response_model=OdooReadOnlyDemoAuditResponse,
)
def get_odoo_read_only_demo_audit_endpoint(db: Session = Depends(get_db)):
    result = OdooReadOnlyDemoAuditService(db).get_audit()
    return OdooReadOnlyDemoAuditResponse(
        events=[OdooReadOnlyDemoAuditEventResponse(**event) for event in result.events]
    )
