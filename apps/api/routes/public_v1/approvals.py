"""Approval records for execution permit binding (Phase 15, master spec 19.3).

Not in the spec's explicit path list -- a standalone approval-creation
endpoint is needed before a run can bind an `approval_id`, and nothing else
in this codebase creates one. Old product approval routes stay legacy.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.execution_permits import ApprovalCreateRequest, ApprovalResponse
from erpguard.domain.execution.approval_service import ApprovalNotFound, ApprovalService
from erpguard.domain.identity.auth import Principal

router = APIRouter(prefix="/v1/approvals", tags=["approvals"])


@router.post("", response_model=ApprovalResponse, status_code=status.HTTP_201_CREATED)
def create_approval(
    request: ApprovalCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> ApprovalResponse:
    row = ApprovalService(db).create(tenant_id=principal.tenant_id, actor_id=principal.user_id, scope=request.scope)
    return _response(row)


@router.get("/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ApprovalResponse:
    try:
        row = ApprovalService(db).get(tenant_id=principal.tenant_id, approval_id=approval_id)
    except ApprovalNotFound as exc:
        raise HTTPException(status_code=404, detail="approval_not_found") from exc
    return _response(row)


def _response(row) -> ApprovalResponse:
    return ApprovalResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        actor_id=row.actor_id,
        scope=row.scope,
        created_at=row.created_at.isoformat(),
        used_at=row.used_at.isoformat() if row.used_at else None,
        used_by_run_id=row.used_by_run_id,
    )
