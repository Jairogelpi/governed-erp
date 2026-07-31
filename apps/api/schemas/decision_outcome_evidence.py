from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class EvidenceBundleCreateRequest(BaseModel):
    measurement_plan_id: str | None = None


class EvidenceBundleResponse(BaseModel):
    id: str
    tenant_id: str
    recommendation_id: str
    measurement_plan_id: str | None
    status: str = Field(pattern="^(building|complete|incomplete|sealed)$")
    manifest: list[dict[str, Any]]
    missing_resources: list[str]
    manifest_hash: str
    content_hash: str
    chain_hash: str
    created_by: str
    created_at: str
    sealed_at: str | None
    sealed_by: str | None


class EvidenceBundleVerifyResponse(BaseModel):
    bundle_id: str
    status: str
    verified: bool
    stored_hashes_intact: bool
    live_mismatches: list[str]
    manifest_hash: str
    content_hash: str
    chain_hash: str
