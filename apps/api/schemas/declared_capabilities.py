from __future__ import annotations

from pydantic import BaseModel


class DeclaredCapabilityCreateRequest(BaseModel):
    name: str
    target_model: str
    target_field: str
    field_type: str
    minimum_value: str | None = None
    maximum_value: str | None = None
    allowed_values: list[str] | None = None
    max_records_per_run: int = 1


class DeclaredCapabilityApproveRequest(BaseModel):
    approval_id: str


class DeclaredCapabilityResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    target_model: str
    target_field: str
    field_type: str
    minimum_value: str | None
    maximum_value: str | None
    allowed_values: list[str]
    max_records_per_run: int
    status: str
    content_hash: str
    approval_scope: str
    created_by: str
    approved_by: str | None
    created_at: str
    approved_at: str | None
    activated_at: str | None


class DeclaredCapabilityListResponse(BaseModel):
    items: list[DeclaredCapabilityResponse]
