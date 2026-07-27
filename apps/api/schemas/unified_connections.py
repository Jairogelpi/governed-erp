from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class UnifiedConnectionCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    connector_type: str = Field(min_length=1, max_length=64)
    endpoint: str = Field(min_length=1, max_length=1000)
    auth_type: str = Field(default="api_key", min_length=1, max_length=64)
    secret: str = Field(min_length=1)
    metadata: dict[str, Any] = Field(default_factory=dict)


class UnifiedConnectionResponse(BaseModel):
    id: str
    tenant_id: str
    name: str
    connector_type: str
    endpoint: str
    auth_type: str
    secret_ref: str
    secret_fingerprint: str
    status: str
    metadata: dict[str, Any]
    created_by: str
    secret_redacted: bool = True
