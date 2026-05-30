from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class OdooReadEvidencePackRequest(BaseModel):
    created_by: str = "operator_1"


class OdooReadEvidencePackResponse(BaseModel):
    evidence_pack_id: str
    read_mapping_id: str
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    object_type: str
    status: str
    canonical_object_snapshot: dict[str, Any]
    source_snapshot_redacted: dict[str, Any]
    field_allowlist_used: list[str]
    redacted_fields: list[str]
    safety_summary: dict[str, Any]
    chain_summary: dict[str, Any]
    created_by: str
    blocking_reasons: list[str]
    raw_secret_accessed: bool = False


class OdooReadEvidencePackListResponse(BaseModel):
    evidence_packs: list[OdooReadEvidencePackResponse]


class OdooReadEvidenceAuditEventResponse(BaseModel):
    event_type: str
    evidence_pack_id: str
    read_mapping_id: str
    connection_test_id: str
    adapter_session_id: str
    activation_id: str
    setup_session_id: str
    credential_ref: str
    object_type: str
    status: str
    actor: str
    details: dict[str, Any]
    created_at: datetime


class OdooReadEvidenceAuditResponse(BaseModel):
    events: list[OdooReadEvidenceAuditEventResponse]
