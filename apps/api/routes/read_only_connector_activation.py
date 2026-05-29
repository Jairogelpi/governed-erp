"""Sprint 59 - read-only connector activation API routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from apps.api.schemas.read_only_connector_activation import (
    ReadOnlyActivationApproveRequest,
    ReadOnlyActivationAuditEventResponse,
    ReadOnlyActivationAuditResponse,
    ReadOnlyActivationListResponse,
    ReadOnlyActivationRequestCreate,
    ReadOnlyActivationRequestResponse,
    ReadOnlyActivationResponse,
)
from erpguard.db.session import SessionLocal
from erpguard.product.read_only_connector_activation import (
    ReadOnlyActivationApprovalInput,
    ReadOnlyActivationRequestInput,
    ReadOnlyConnectorActivationService,
)
from erpguard.product.read_only_connector_activation_audit import (
    ReadOnlyConnectorActivationAuditService,
)

router = APIRouter(
    prefix="/v1/operator-console/connectors",
    tags=["Read-Only Connector Activation"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.post(
    "/generated-capabilities/{capability_set_id}/read-only-activation-request",
    response_model=ReadOnlyActivationRequestResponse,
)
def create_read_only_activation_request_endpoint(
    capability_set_id: str,
    request: ReadOnlyActivationRequestCreate,
    db: Session = Depends(get_db),
):
    result = ReadOnlyConnectorActivationService(db).create_request(
        ReadOnlyActivationRequestInput(
            capability_set_id=capability_set_id,
            requested_by=request.requested_by,
            mode=request.mode,
        )
    )
    return ReadOnlyActivationRequestResponse(**result.__dict__)


@router.post(
    "/read-only-activation/{activation_request_id}/approve",
    response_model=ReadOnlyActivationResponse,
)
def approve_read_only_activation_endpoint(
    activation_request_id: str,
    request: ReadOnlyActivationApproveRequest,
    db: Session = Depends(get_db),
):
    result = ReadOnlyConnectorActivationService(db).approve(
        ReadOnlyActivationApprovalInput(
            activation_request_id=activation_request_id,
            approved_by=request.approved_by,
        )
    )
    return ReadOnlyActivationResponse(**result.__dict__)


@router.get(
    "/read-only-activation/{activation_id}",
    response_model=ReadOnlyActivationResponse,
)
def get_read_only_activation_endpoint(
    activation_id: str,
    db: Session = Depends(get_db),
):
    result = ReadOnlyConnectorActivationService(db).get_activation(activation_id)
    if result is None:
        return JSONResponse(
            status_code=404, content={"detail": "Read-only activation not found"}
        )
    return ReadOnlyActivationResponse(**result)


@router.get(
    "/read-only-activations",
    response_model=ReadOnlyActivationListResponse,
)
def list_read_only_activations_endpoint(db: Session = Depends(get_db)):
    result = ReadOnlyConnectorActivationService(db).list_activations()
    return ReadOnlyActivationListResponse(
        activations=[ReadOnlyActivationResponse(**item) for item in result]
    )


@router.get(
    "/read-only-activation-audit",
    response_model=ReadOnlyActivationAuditResponse,
)
def get_read_only_activation_audit_endpoint(db: Session = Depends(get_db)):
    result = ReadOnlyConnectorActivationAuditService(db).get_audit()
    return ReadOnlyActivationAuditResponse(
        events=[ReadOnlyActivationAuditEventResponse(**event) for event in result.events]
    )
