from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class FakeERPEvidencePackCreateRequest(BaseModel):
    execution_id: str


class FakeERPEvidencePackResponse(BaseModel):
    pack_id: str
    execution_id: str
    version_id: str
    skill_id: str
    dry_run_id: str
    result_snapshot: dict[str, Any]
    steps_snapshot: list[dict[str, Any]]
    safety_summary: dict[str, Any]
    audit_snapshot: list[dict[str, Any]]
    created: bool
    blocking_reasons: list[str]
