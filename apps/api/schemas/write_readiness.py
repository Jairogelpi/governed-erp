from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class WriteReadinessAssessmentResponse(BaseModel):
    assessment_id: str
    skill_id: str
    skill_version_id: str
    status: str
    write_candidates: list[dict[str, Any]]
    risk_matrix: list[dict[str, Any]]
    overall_risk_level: str
    can_certify_write_readiness: bool
    blocking_issues: list[str]
    permission_preview: dict[str, Any] | None = None
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    created_at: str | None = None


class WriteImpactPreviewResponse(BaseModel):
    impact_id: str
    assessment_id: str
    skill_id: str
    impact_summary: str
    affected_models: list[str]
    estimated_record_count: int
    reversible: bool
    rollback_strategy: str
    can_execute_real_writes: bool = False
    created_at: str | None = None


class WriteRollbackPlanResponse(BaseModel):
    plan_id: str
    assessment_id: str
    skill_id: str
    rollback_steps: list[str]
    backup_strategy: str
    estimated_rollback_time_minutes: int
    can_execute_real_writes: bool = False
    created_at: str | None = None


class WriteReadinessCertificationResponse(BaseModel):
    certification_id: str
    skill_id: str
    assessment_id: str
    impact_preview_id: str | None = None
    rollback_plan_id: str | None = None
    certification_status: str
    overall_risk_level: str
    dual_approval_required: bool = True
    can_certify_real_execution: bool = False
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    approved_for_real_execution: bool = False
    evidence: dict[str, Any]
    created_at: str | None = None


class WriteReadinessSummaryResponse(BaseModel):
    skill_id: str
    has_assessment: bool
    has_impact_preview: bool
    has_rollback_plan: bool
    has_certification: bool
    overall_risk_level: str | None = None
    certification_status: str | None = None
    can_certify_real_execution: bool = False
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    approved_for_real_execution: bool = False
