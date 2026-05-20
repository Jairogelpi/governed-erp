from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class BusinessAnalysisSampleLimits(BaseModel):
    sales_orders: int = Field(default=5, ge=0, le=20)
    products: int = Field(default=5, ge=0, le=20)
    custom_fields: int = Field(default=50, ge=0, le=500)


class BusinessAnalysisRequest(BaseModel):
    include_samples: bool = True
    sample_limits: BusinessAnalysisSampleLimits = Field(default_factory=BusinessAnalysisSampleLimits)
    max_opportunities: int = Field(default=5, ge=1, le=10)


class BusinessSnapshotModel(BaseModel):
    snapshot_id: str
    connection_id: str
    status: str
    read_only_mode: bool = True
    odoo: dict[str, Any]
    modules: dict[str, bool]
    models: dict[str, Any]
    fields: dict[str, Any]
    samples: dict[str, Any]
    detected: dict[str, Any]
    warnings: list[dict[str, Any]] = Field(default_factory=list)
    next_recommended_action: str
    summary: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class BusinessSignalModel(BaseModel):
    signal_id: str
    code: str
    title: str
    severity: str
    message: str
    score: int
    evidence: dict[str, Any] = Field(default_factory=dict)


class OpportunityROIModel(BaseModel):
    implementation_effort_hours: float
    estimated_monthly_savings_hours: float
    estimated_monthly_value_eur: float
    payback_weeks: float
    confidence: float
    score: int
    rationale: str


class BusinessOpportunityModel(BaseModel):
    opportunity_id: str
    code: str
    title: str
    description: str
    recommendation: str
    category: str
    priority: int
    signal_codes: list[str] = Field(default_factory=list)
    roi: OpportunityROIModel
    evidence: dict[str, Any] = Field(default_factory=dict)
    card_label: str | None = None


class OpportunityScanModel(BaseModel):
    scan_id: str
    snapshot_id: str
    connection_id: str
    status: str
    opportunity_count: int
    signal_count: int
    roi_summary: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class BusinessAnalysisResult(BaseModel):
    connection_id: str
    snapshot_id: str
    scan_id: str
    status: str
    read_only_mode: bool = True
    snapshot: BusinessSnapshotModel
    signals: list[BusinessSignalModel] = Field(default_factory=list)
    opportunities: list[BusinessOpportunityModel] = Field(default_factory=list)
    recommendation_cards: list[BusinessOpportunityModel] = Field(default_factory=list)
    roi_summary: dict[str, Any] = Field(default_factory=dict)
    next_recommended_action: str
    secrets_redacted: bool = True


class AutomationDraftModel(BaseModel):
    draft_id: str
    opportunity_id: str
    scan_id: str
    snapshot_id: str
    connection_id: str
    name: str
    description: str
    status: str
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    draft_package: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None
    secrets_redacted: bool = True


class DraftGuardModel(BaseModel):
    name: str
    description: str
    enforced: bool = True


class DraftInputFieldModel(BaseModel):
    name: str
    type: str
    description: str
    required: bool = True
    example: Any = None


class DraftOutputFieldModel(BaseModel):
    name: str
    type: str
    description: str


class DraftTestCaseModel(BaseModel):
    case_id: str
    name: str
    inputs: dict[str, Any]
    expected_outcome: str
    expected_decision: str


class DraftReviewModel(BaseModel):
    review_id: str
    draft_id: str
    opportunity_id: str
    connection_id: str
    guards: list[DraftGuardModel]
    input_schema: list[DraftInputFieldModel]
    output_schema: list[DraftOutputFieldModel]
    test_cases: list[DraftTestCaseModel]
    status: str
    skill_id: str | None = None
    skill_version_id: str | None = None
    created_at: str | None = None


class CompiledSkillModel(BaseModel):
    skill_id: str
    version_id: str
    draft_id: str
    review_id: str
    opportunity_id: str
    connection_id: str
    name: str
    description: str
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    requires_approval_before_activation: bool = True
    guards: list[str]
    input_schema: list[dict[str, Any]]
    output_schema: list[dict[str, Any]]
    test_cases: list[dict[str, Any]]
    created_at: str | None = None


class ValidationIssueModel(BaseModel):
    code: str
    message: str
    severity: str = "blocking"


class DraftValidationResultModel(BaseModel):
    draft_id: str
    passed: bool
    issues: list[ValidationIssueModel] = Field(default_factory=list)


class DryRunCaseResultModel(BaseModel):
    case_id: str
    name: str
    inputs: dict[str, Any]
    expected_decision: str
    actual_decision: str
    passed: bool
    guard_violations: list[str] = Field(default_factory=list)
    notes: str = ""


class DryRunProofModel(BaseModel):
    proof_id: str
    skill_id: str
    version_id: str
    draft_id: str
    review_id: str
    status: str
    cases_total: int
    cases_passed: int
    runtime_mode: str = "dry_run_only"
    write_actions: bool = False
    requires_approval_before_activation: bool = True
    guards: list[str] = Field(default_factory=list)
    case_results: list[DryRunCaseResultModel] = Field(default_factory=list)
    created_at: str | None = None


class ApprovalActorModel(BaseModel):
    type: str
    id: str
    display_name: str


class ApprovalRequestModel(BaseModel):
    request_id: str
    skill_id: str
    skill_version_id: str
    requested_by: ApprovalActorModel
    reason: str
    status: str
    can_execute_real_writes: bool = False
    context: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ApprovalDecisionModel(BaseModel):
    decision_id: str
    approval_request_id: str
    skill_id: str
    decided_by: ApprovalActorModel
    decision: str
    reason: str
    can_execute_real_writes: bool = False
    approved_for_real_execution: bool = False
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class GateCheckModel(BaseModel):
    check_id: str
    description: str
    passed: bool
    detail: str = ""


class ActivationGateModel(BaseModel):
    gate_id: str
    skill_id: str
    approval_request_id: str | None = None
    gate_status: str
    can_activate: bool
    can_execute_real_writes: bool = False
    approved_for_real_execution: bool = False
    checks: list[GateCheckModel] = Field(default_factory=list)
    created_at: str | None = None


class GovernanceSummaryModel(BaseModel):
    skill_id: str
    skill_name: str
    skill_status: str
    can_execute_real_writes: bool = False
    approved_for_real_execution: bool = False
    approval_request: ApprovalRequestModel | None = None
    latest_decision: ApprovalDecisionModel | None = None
    latest_gate: ActivationGateModel | None = None
    approval_history: list[ApprovalDecisionModel] = Field(default_factory=list)
    governance_state: str = "not_submitted"
    next_required_action: str = ""
    created_at: str | None = None


class ExecutionRequestModel(BaseModel):
    request_id: str
    skill_id: str
    skill_version_id: str
    approval_request_id: str | None = None
    requested_by: dict[str, Any]
    inputs: dict[str, Any]
    status: str
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    idempotency_key: str
    created_at: str | None = None


class WriteCandidateModel(BaseModel):
    model: str
    method: str
    args: dict[str, Any]
    blocked: bool = True
    blocked_reason: str = "ALLOW_REAL_ODOO_WRITES=false"


class SimulatedExecutionStepModel(BaseModel):
    step_id: str
    step_type: str
    description: str
    status: str
    inputs: dict[str, Any] = Field(default_factory=dict)
    simulated_output: dict[str, Any] = Field(default_factory=dict)
    write_candidate: WriteCandidateModel | None = None


class SimulatedExecutionPlanModel(BaseModel):
    plan_id: str
    skill_id: str
    steps: list[SimulatedExecutionStepModel] = Field(default_factory=list)
    total_steps: int
    blocked_write_candidates: int = 0
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False


class BlockedWriteEvidenceModel(BaseModel):
    evidence_id: str
    execution_run_id: str
    execution_request_id: str
    skill_id: str
    attempted_model: str
    attempted_method: str
    attempted_args: dict[str, Any]
    blocked_reason: str
    created_at: str | None = None


class ExecutionRunModel(BaseModel):
    run_id: str
    execution_request_id: str
    skill_id: str
    status: str
    plan: SimulatedExecutionPlanModel
    result: dict[str, Any] = Field(default_factory=dict)
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    blocked_write_count: int = 0
    created_at: str | None = None
    finished_at: str | None = None


class ExecutionRunStepModel(BaseModel):
    step_id: str
    step_type: str
    status: str
    input: dict[str, Any] = Field(default_factory=dict)
    output: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class ExecutionTimelineModel(BaseModel):
    run_id: str
    steps: list[ExecutionRunStepModel] = Field(default_factory=list)
    total_steps: int
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False


# Sprint 6 — Controlled Real Read Execution & Live Evidence

class ConnectionContextModel(BaseModel):
    connection_id: str
    skill_id: str
    erp_type: str
    connection_status: str
    url: str
    database: str
    username: str
    has_credentials: bool = True
    secrets_redacted: bool = True
    resolved: bool
    missing_reason: str | None = None


class LiveReadPolicyViolation(BaseModel):
    code: str
    message: str
    blocking: bool = True


class LiveReadPolicyResult(BaseModel):
    passed: bool
    allow_real_odoo_reads: bool = True
    allow_live_read_evidence: bool = True
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    violations: list[LiveReadPolicyViolation] = Field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "passed": self.passed,
            "allow_real_odoo_reads": self.allow_real_odoo_reads,
            "allow_live_read_evidence": self.allow_live_read_evidence,
            "can_execute_real_writes": False,
            "real_erp_writes_enabled": False,
            "violations": [{"code": v.code, "message": v.message, "blocking": v.blocking} for v in self.violations],
        }


class LiveReadStepModel(BaseModel):
    step_id: str
    step_type: str
    description: str
    odoo_model: str
    odoo_method: str
    domain: list[Any] = Field(default_factory=list)
    fields: list[str] = Field(default_factory=list)
    limit: int | None = None
    status: str = "pending"
    real_output: dict[str, Any] | None = None
    write_candidate: WriteCandidateModel | None = None
    read_only: bool = True


class LiveReadPlanModel(BaseModel):
    plan_id: str
    skill_id: str
    connection_id: str | None = None
    steps: list[LiveReadStepModel] = Field(default_factory=list)
    total_steps: int
    real_read_steps: int = 0
    blocked_write_candidates: int = 0
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    allow_real_odoo_reads: bool = True


class LiveReadEvidenceModel(BaseModel):
    evidence_id: str
    live_read_run_id: str
    execution_request_id: str
    skill_id: str
    step_id: str
    odoo_model: str
    odoo_method: str
    query_summary: dict[str, Any] = Field(default_factory=dict)
    records_fetched: int
    result_summary: dict[str, Any] = Field(default_factory=dict)
    read_only: bool = True
    created_at: str | None = None


class LiveReadExecutionRequestModel(BaseModel):
    request_id: str
    skill_id: str
    skill_version_id: str
    connection_id: str | None = None
    approval_request_id: str | None = None
    requested_by: dict[str, Any]
    inputs: dict[str, Any]
    status: str
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    allow_real_odoo_reads: bool = True
    idempotency_key: str
    created_at: str | None = None


class LiveReadRunModel(BaseModel):
    run_id: str
    execution_request_id: str
    skill_id: str
    connection_id: str | None = None
    status: str
    plan: LiveReadPlanModel
    result: dict[str, Any] = Field(default_factory=dict)
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    allow_real_odoo_reads: bool = True
    real_read_count: int = 0
    blocked_write_count: int = 0
    created_at: str | None = None
    finished_at: str | None = None


# Sprint 7 — Write Capability Readiness & Risk Certification

class WriteDetectedCandidateModel(BaseModel):
    candidate_id: str
    opportunity_code: str
    odoo_model: str
    write_method: str
    description: str
    blocked: bool = True
    blocked_reason: str = "ALLOW_REAL_ODOO_WRITES=false"
    risk_level: str = "unknown"


class WriteRiskMatrixEntryModel(BaseModel):
    candidate_id: str
    odoo_model: str
    write_method: str
    risk_level: str
    risk_code: str
    rationale: str
    reversible: bool
    requires_dual_approval: bool = True
    can_execute_real_writes: bool = False


class WritePermissionPreviewModel(BaseModel):
    skill_id: str
    required_odoo_permissions: list[str] = Field(default_factory=list)
    missing_permissions: list[str] = Field(default_factory=list)
    permission_gaps: list[str] = Field(default_factory=list)
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False


class WriteReadinessAssessmentModel(BaseModel):
    assessment_id: str
    skill_id: str
    skill_version_id: str
    status: str
    write_candidates: list[WriteDetectedCandidateModel] = Field(default_factory=list)
    risk_matrix: list[WriteRiskMatrixEntryModel] = Field(default_factory=list)
    overall_risk_level: str
    can_certify_write_readiness: bool
    blocking_issues: list[str] = Field(default_factory=list)
    permission_preview: WritePermissionPreviewModel | None = None
    can_execute_real_writes: bool = False
    real_erp_writes_enabled: bool = False
    created_at: str | None = None


class WriteImpactPreviewModel(BaseModel):
    impact_id: str
    assessment_id: str
    skill_id: str
    impact_summary: str
    affected_models: list[str] = Field(default_factory=list)
    estimated_record_count: int
    reversible: bool
    rollback_strategy: str
    can_execute_real_writes: bool = False
    created_at: str | None = None


class WriteRollbackPlanModel(BaseModel):
    plan_id: str
    assessment_id: str
    skill_id: str
    rollback_steps: list[str] = Field(default_factory=list)
    backup_strategy: str
    estimated_rollback_time_minutes: int
    can_execute_real_writes: bool = False
    created_at: str | None = None


class WriteReadinessCertificationModel(BaseModel):
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
    evidence: dict[str, Any] = Field(default_factory=dict)
    created_at: str | None = None


class WriteReadinessSummaryModel(BaseModel):
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
