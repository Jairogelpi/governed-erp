from __future__ import annotations

from collections.abc import Callable, Generator

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from erpguard.config import settings
from erpguard.db.model_packages.identity import IdentityMembership, IdentityUser
from erpguard.db.session import SessionLocal
from erpguard.domain.identity.auth import AuthenticationError, Principal, verify_token


_bearer = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_principal(
    credentials: HTTPAuthorizationCredentials | None = Security(_bearer),
    db: Session = Depends(get_db),
) -> Principal:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="authentication_required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not settings.auth_secret:
        raise HTTPException(status_code=503, detail="authentication_not_configured")
    try:
        user_id, tenant_id = verify_token(credentials.credentials, settings.auth_secret)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user = db.get(IdentityUser, user_id)
    membership = (
        db.query(IdentityMembership)
        .filter(
            IdentityMembership.user_id == user_id,
            IdentityMembership.tenant_id == tenant_id,
            IdentityMembership.status == "active",
        )
        .one_or_none()
    )
    if user is None or user.status != "active" or membership is None:
        raise HTTPException(status_code=403, detail="identity_membership_required")
    return Principal(user_id=user.id, tenant_id=tenant_id, role_name=membership.role_name)


def require_role(role_name: str) -> Callable:
    def dependency(principal: Principal = Depends(get_current_principal)) -> Principal:
        if principal.role_name != role_name and principal.role_name != "admin":
            raise HTTPException(status_code=403, detail="role_required")
        return principal

    return dependency

