from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.declared_capabilities import (
    DeclaredCapabilityApproveRequest,
    DeclaredCapabilityCreateRequest,
    DeclaredCapabilityListResponse,
    DeclaredCapabilityResponse,
)
from erpguard.domain.declared_capabilities.service import (
    DeclaredCapabilityDenied,
    DeclaredCapabilityNotFound,
    DeclaredCapabilityService,
    DeclaredCapabilityTransitionError,
    DeclaredCapabilityValidationError,
)
from erpguard.domain.identity.auth import Principal

router = APIRouter(prefix="/v1/declared-capabilities", tags=["declared_capabilities"])


@router.post("", response_model=DeclaredCapabilityResponse, status_code=status.HTTP_201_CREATED)
def declare_capability(
    request: DeclaredCapabilityCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> DeclaredCapabilityResponse:
    try:
        row = DeclaredCapabilityService(db).declare(
            tenant_id=principal.tenant_id,
            name=request.name,
            target_model=request.target_model,
            operation=request.operation,
            target_field=request.target_field,
            field_type=request.field_type,
            created_by=principal.user_id,
            minimum_value=request.minimum_value,
            maximum_value=request.maximum_value,
            allowed_values=request.allowed_values,
            required_fields=request.required_fields,
            idempotency_field=request.idempotency_field,
            max_records_per_run=request.max_records_per_run,
        )
    except DeclaredCapabilityDenied as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except DeclaredCapabilityValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.get("", response_model=DeclaredCapabilityListResponse)
def list_capabilities(
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> DeclaredCapabilityListResponse:
    rows = DeclaredCapabilityService(db).list(tenant_id=principal.tenant_id)
    return DeclaredCapabilityListResponse(items=[_response(row) for row in rows])


@router.get("/{capability_id}", response_model=DeclaredCapabilityResponse)
def get_capability(
    capability_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> DeclaredCapabilityResponse:
    try:
        row = DeclaredCapabilityService(db).get(tenant_id=principal.tenant_id, capability_id=capability_id)
    except DeclaredCapabilityNotFound as exc:
        raise HTTPException(status_code=404, detail="declared_capability_not_found") from exc
    return _response(row)


@router.post("/{capability_id}/approve", response_model=DeclaredCapabilityResponse)
def approve_capability(
    capability_id: str,
    request: DeclaredCapabilityApproveRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> DeclaredCapabilityResponse:
    try:
        row = DeclaredCapabilityService(db).approve(
            tenant_id=principal.tenant_id,
            capability_id=capability_id,
            approval_id=request.approval_id,
            approver_actor_id=principal.user_id,
        )
    except DeclaredCapabilityNotFound as exc:
        raise HTTPException(status_code=404, detail="declared_capability_not_found") from exc
    except DeclaredCapabilityValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.post("/{capability_id}/activate", response_model=DeclaredCapabilityResponse)
def activate_capability(
    capability_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> DeclaredCapabilityResponse:
    service = DeclaredCapabilityService(db)
    try:
        row = service.activate(tenant_id=principal.tenant_id, capability_id=capability_id)
    except DeclaredCapabilityNotFound as exc:
        raise HTTPException(status_code=404, detail="declared_capability_not_found") from exc
    except DeclaredCapabilityTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


def _response(row) -> DeclaredCapabilityResponse:
    return DeclaredCapabilityResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        name=row.name,
        operation=row.operation,
        target_model=row.target_model,
        target_field=row.target_field,
        field_type=row.field_type,
        minimum_value=row.minimum_value,
        maximum_value=row.maximum_value,
        allowed_values=json.loads(row.allowed_values_json or "[]"),
        required_fields=json.loads(row.required_fields_json or "{}"),
        idempotency_field=row.idempotency_field,
        max_records_per_run=row.max_records_per_run,
        status=row.status,
        content_hash=row.content_hash,
        approval_scope=DeclaredCapabilityService.approval_scope(row),
        created_by=row.created_by,
        approved_by=row.approved_by,
        created_at=row.created_at.isoformat(),
        approved_at=row.approved_at.isoformat() if row.approved_at else None,
        activated_at=row.activated_at.isoformat() if row.activated_at else None,
    )
