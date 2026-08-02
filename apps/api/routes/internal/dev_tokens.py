"""Spec 94 -- development/demo token bootstrap. This codebase's identity
layer (`erpguard/domain/identity/auth.py::issue_token`) is deliberately
"trusted bootstrap/test tooling, never from a public route" -- there is no
real login (no password, no OAuth, no session) anywhere in this system.

This endpoint does not add one. It exposes the same trusted-bootstrap
token issuance the test suite already uses, through the same internal-only
gate `/demo` and `/fake-erp/*` already sit behind (`ERPGUARD_INTERNAL_SURFACES`,
off by default, never mounted in the public app). It exists so the web
app's local/demo Settings screen has something to call instead of a
developer hand-editing the database -- it is explicitly not a production
authentication mechanism, and the web app's onboarding copy says so.
"""

from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db
from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.domain.identity.auth import issue_token

router = APIRouter(prefix="/internal/dev-tokens", tags=["internal-dev-tokens"])


class DevTokenRequest(BaseModel):
    tenant_id: str = Field(min_length=1)
    role_name: str = Field(default="admin", pattern="^(admin|operator|viewer)$")
    display_name: str = Field(default="Dev user", min_length=1)


class DevTokenResponse(BaseModel):
    token: str
    user_id: str
    tenant_id: str
    role_name: str
    expires_in_seconds: int


@router.post("", response_model=DevTokenResponse, status_code=201)
def create_dev_token(request: DevTokenRequest, db: Session = Depends(get_db)) -> DevTokenResponse:
    suffix = uuid4().hex
    user_id = f"dev-user-{suffix}"
    db.add(IdentityUser(id=user_id, email=f"{suffix}@dev.local", display_name=request.display_name))
    db.add(IdentityMembership(
        id=f"dev-membership-{suffix}", tenant_id=request.tenant_id, user_id=user_id,
        role_name=request.role_name, status="active",
    ))
    db.commit()

    expires_in_seconds = 3600
    token = issue_token(
        user_id, request.tenant_id, settings.auth_secret or "insecure-dev-secret",
        expires_at=int(time.time()) + expires_in_seconds,
    )
    return DevTokenResponse(
        token=token, user_id=user_id, tenant_id=request.tenant_id,
        role_name=request.role_name, expires_in_seconds=expires_in_seconds,
    )
