from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_current_principal, get_db, require_role
from apps.api.schemas.identity import (
    CurrentUserResponse,
    MembershipCreateRequest,
    MembershipResponse,
)
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.domain.identity.auth import Principal


router = APIRouter(prefix="/v1/identity", tags=["identity"])


@router.get("/me", response_model=CurrentUserResponse)
def get_current_user_endpoint(
    principal: Principal = Depends(get_current_principal),
) -> CurrentUserResponse:
    return CurrentUserResponse(
        user_id=principal.user_id,
        tenant_id=principal.tenant_id,
        role_name=principal.role_name,
    )


@router.post(
    "/tenants/{tenant_id}/members",
    response_model=MembershipResponse,
    status_code=status.HTTP_201_CREATED,
)
def add_membership_endpoint(
    tenant_id: str,
    request: MembershipCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> MembershipResponse:
    if principal.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_scope_violation")
    if request.tenant_id is not None and request.tenant_id != tenant_id:
        raise HTTPException(status_code=403, detail="tenant_scope_violation")
    if db.get(IdentityUser, request.user_id) is None:
        raise HTTPException(status_code=404, detail="user_not_found")
    existing = (
        db.query(IdentityMembership)
        .filter(
            IdentityMembership.tenant_id == tenant_id,
            IdentityMembership.user_id == request.user_id,
        )
        .one_or_none()
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="membership_exists")
    membership = IdentityMembership(
        id=f"membership_{uuid4().hex}",
        tenant_id=tenant_id,
        user_id=request.user_id,
        role_name=request.role_name,
        status="active",
    )
    db.add(membership)
    db.commit()
    return MembershipResponse(
        membership_id=membership.id,
        user_id=membership.user_id,
        tenant_id=membership.tenant_id,
        role_name=membership.role_name,
        actor_id=principal.user_id,
    )

