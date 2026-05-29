"""Sprint 56 — ERP Fingerprinting Plan API schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field


class FingerprintingPlanRequest(BaseModel):
    setup_session_id: str
    credential_ref: str
    created_by: str = "operator_1"
    manual_hint: str | None = None


class FingerprintingPlanResponse(BaseModel):
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    connector_name: str
    erp_url_host: str
    environment_type: str
    status: str
    adapter_candidates: list[dict]
    planned_checks: list[dict]
    risk_summary: dict
    next_safe_step: str | None = None
    confidence: float = 0.0
    blocking_reasons: list[str] = Field(default_factory=list)
    will_connect: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    fingerprint_performed: bool = False
    schema_inspection_performed: bool = False
    capability_generation_performed: bool = False
    read_only_activation_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


class FingerprintingPlanDetailResponse(BaseModel):
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    connector_name: str
    erp_url_host: str
    environment_type: str
    status: str
    adapter_candidates: list[dict]
    planned_checks: list[dict]
    risk_summary: dict
    next_safe_step: str | None = None
    confidence: float = 0.0
    blocking_reasons: list[str] = Field(default_factory=list)
    will_connect: bool = False
    external_http_performed: bool = False
    login_attempted: bool = False
    fingerprint_performed: bool = False
    schema_inspection_performed: bool = False
    capability_generation_performed: bool = False
    read_only_activation_performed: bool = False
    credentials_exposed: bool = False
    raw_secret_accessed: bool = False


class FingerprintingPlanListItem(BaseModel):
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    connector_name: str
    erp_url_host: str
    status: str
    confidence: float = 0.0


class FingerprintingPlanListResponse(BaseModel):
    plans: list[FingerprintingPlanListItem]


class FingerprintingAuditEventResponse(BaseModel):
    id: str
    fingerprint_plan_id: str
    setup_session_id: str
    credential_ref: str
    event_type: str
    status: str
    details: str
    created_at: str


class FingerprintingAuditResponse(BaseModel):
    events: list[FingerprintingAuditEventResponse]
