from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


RoleName = Literal["admin", "operator", "viewer"]


class CurrentUserResponse(BaseModel):
    user_id: str
    tenant_id: str
    role_name: RoleName


class MembershipCreateRequest(BaseModel):
    user_id: str
    role_name: RoleName
    tenant_id: str | None = None
    actor: str | None = None


class MembershipResponse(BaseModel):
    membership_id: str
    user_id: str
    tenant_id: str
    role_name: RoleName
    actor_id: str

