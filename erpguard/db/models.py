from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    erp_type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class PreflightCase(Base):
    __tablename__ = "preflight_cases"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False)
    actor_json: Mapped[str] = mapped_column(Text, nullable=False)
    action_json: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_action: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_object: Mapped[str] = mapped_column(Text, nullable=False)
    state_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    simulation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class InvariantResult(Base):
    __tablename__ = "invariant_results"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    preflight_case_id: Mapped[str] = mapped_column(Text, nullable=False)
    invariant_id: Mapped[str] = mapped_column(Text, nullable=False)
    invariant_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_action: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_object: Mapped[str] = mapped_column(Text, nullable=False)
    erp_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class SkillVersion(Base):
    __tablename__ = "skill_versions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    skill_package_json: Mapped[str] = mapped_column(Text, nullable=False)
    runtime_type: Mapped[str] = mapped_column(Text, nullable=False)
    llm_required_for_repeated_runs: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SkillRun(Base):
    __tablename__ = "skill_runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_version_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    estimated_tokens_saved: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SkillRunStep(Base):
    __tablename__ = "skill_run_steps"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    step_id: Mapped[str] = mapped_column(Text, nullable=False)
    step_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    output_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    error_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RecordingSession(Base):
    __tablename__ = "recording_sessions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    erp_type: Mapped[str] = mapped_column(Text, nullable=False)
    target_base_url: Mapped[str] = mapped_column(Text, nullable=False)
    created_by_actor_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class RecordingEvent(Base):
    __tablename__ = "recording_events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    recording_session_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_index: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    page_title: Mapped[str | None] = mapped_column(Text, nullable=True)
    element_role: Mapped[str | None] = mapped_column(Text, nullable=True)
    element_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    element_label: Mapped[str | None] = mapped_column(Text, nullable=True)
    selector: Mapped[str | None] = mapped_column(Text, nullable=True)
    input_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    before_text_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    after_text_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    screenshot_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BusinessSnapshot(Base):
    __tablename__ = "business_snapshots"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False)
    erp_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    read_only_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BusinessSignal(Base):
    __tablename__ = "business_signals"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    business_snapshot_id: Mapped[str] = mapped_column(Text, nullable=False)
    signal_code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class OpportunityScan(Base):
    __tablename__ = "opportunity_scans"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    business_snapshot_id: Mapped[str] = mapped_column(Text, nullable=False)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    opportunity_scan_id: Mapped[str] = mapped_column(Text, nullable=False)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    signal_codes_json: Mapped[str] = mapped_column(Text, nullable=False)
    roi_json: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class WriteReadinessAssessment(Base):
    __tablename__ = "write_readiness_assessments"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_version_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    write_candidates_json: Mapped[str] = mapped_column(Text, nullable=False)
    risk_matrix_json: Mapped[str] = mapped_column(Text, nullable=False)
    overall_risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    can_certify_write_readiness: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocking_issues_json: Mapped[str] = mapped_column(Text, nullable=False)
    permission_preview_json: Mapped[str] = mapped_column(Text, nullable=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    real_erp_writes_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class WriteImpactPreview(Base):
    __tablename__ = "write_impact_previews"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    assessment_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    impact_summary: Mapped[str] = mapped_column(Text, nullable=False)
    affected_models_json: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    reversible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    rollback_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class WriteRollbackPlan(Base):
    __tablename__ = "write_rollback_plans"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    assessment_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    rollback_steps_json: Mapped[str] = mapped_column(Text, nullable=False)
    backup_strategy: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_rollback_time_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class WriteReadinessCertification(Base):
    __tablename__ = "write_readiness_certifications"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    assessment_id: Mapped[str] = mapped_column(Text, nullable=False)
    impact_preview_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    rollback_plan_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    certification_status: Mapped[str] = mapped_column(Text, nullable=False)
    overall_risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    dual_approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    can_certify_real_execution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    real_erp_writes_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_for_real_execution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


# Sprint 8 — First Real Write Pilot (mail.message.create only)

class WritePilotRequest(Base):
    __tablename__ = "write_pilot_requests"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    certification_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_json: Mapped[str] = mapped_column(Text, nullable=False)
    approver_1_json: Mapped[str] = mapped_column(Text, nullable=False)
    approver_2_json: Mapped[str] = mapped_column(Text, nullable=False)
    target_model: Mapped[str] = mapped_column(Text, nullable=False)
    target_res_model: Mapped[str] = mapped_column(Text, nullable=False)
    target_res_id: Mapped[int] = mapped_column(Integer, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    allow_r1_real_write_pilot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_generic_real_odoo_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_r3_r4_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class WritePilotRun(Base):
    __tablename__ = "write_pilot_runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    executed_action: Mapped[str] = mapped_column(Text, nullable=False)
    pre_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    post_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    policy_passed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_r1_real_write_pilot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_generic_real_odoo_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_r3_r4_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class WritePilotEvidence(Base):
    __tablename__ = "write_pilot_evidence"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    run_id: Mapped[str] = mapped_column(Text, nullable=False)
    request_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    action_taken: Mapped[str] = mapped_column(Text, nullable=False)
    target_model: Mapped[str] = mapped_column(Text, nullable=False)
    target_res_model: Mapped[str] = mapped_column(Text, nullable=False)
    target_res_id: Mapped[str] = mapped_column(Text, nullable=False)
    pre_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    post_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    allow_r1_real_write_pilot: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_generic_real_odoo_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LiveReadExecutionRequest(Base):
    __tablename__ = "live_read_execution_requests"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_version_id: Mapped[str] = mapped_column(Text, nullable=False)
    connection_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    approval_request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_json: Mapped[str] = mapped_column(Text, nullable=False)
    inputs_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    real_erp_writes_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_real_odoo_reads: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class LiveReadRun(Base):
    __tablename__ = "live_read_runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    execution_request_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    connection_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    real_erp_writes_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    allow_real_odoo_reads: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    real_read_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    blocked_write_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class LiveReadEvidence(Base):
    __tablename__ = "live_read_evidence"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    live_read_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    execution_request_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    step_id: Mapped[str] = mapped_column(Text, nullable=False)
    odoo_model: Mapped[str] = mapped_column(Text, nullable=False)
    odoo_method: Mapped[str] = mapped_column(Text, nullable=False)
    query_summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    records_fetched: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    result_summary_json: Mapped[str] = mapped_column(Text, nullable=False)
    read_only: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ExecutionRequest(Base):
    __tablename__ = "execution_requests"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_version_id: Mapped[str] = mapped_column(Text, nullable=False)
    approval_request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    requested_by_json: Mapped[str] = mapped_column(Text, nullable=False)
    inputs_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    real_erp_writes_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ExecutionRun(Base):
    __tablename__ = "execution_runs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    execution_request_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    result_json: Mapped[str] = mapped_column(Text, nullable=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    real_erp_writes_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocked_write_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ExecutionRunStep(Base):
    __tablename__ = "execution_run_steps"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    execution_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    step_id: Mapped[str] = mapped_column(Text, nullable=False)
    step_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    input_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    execution_request_id: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class BlockedWriteEvidenceRecord(Base):
    __tablename__ = "blocked_write_evidence"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    execution_run_id: Mapped[str] = mapped_column(Text, nullable=False)
    execution_request_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    attempted_model: Mapped[str] = mapped_column(Text, nullable=False)
    attempted_method: Mapped[str] = mapped_column(Text, nullable=False)
    attempted_args_json: Mapped[str] = mapped_column(Text, nullable=False)
    blocked_reason: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SkillApprovalRequest(Base):
    __tablename__ = "skill_approval_requests"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_version_id: Mapped[str] = mapped_column(Text, nullable=False)
    requested_by_json: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    context_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class SkillApprovalDecision(Base):
    __tablename__ = "skill_approval_decisions"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    approval_request_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    decided_by_json: Mapped[str] = mapped_column(Text, nullable=False)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_for_real_execution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SkillActivationGateEvaluation(Base):
    __tablename__ = "skill_activation_gate_evaluations"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    approval_request_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    gate_status: Mapped[str] = mapped_column(Text, nullable=False)
    can_activate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    can_execute_real_writes: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    approved_for_real_execution: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    checks_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class SkillDryRunProof(Base):
    __tablename__ = "skill_dry_run_proofs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    skill_id: Mapped[str] = mapped_column(Text, nullable=False)
    skill_version_id: Mapped[str] = mapped_column(Text, nullable=False)
    draft_id: Mapped[str] = mapped_column(Text, nullable=False)
    review_id: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    cases_total: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    cases_passed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    proof_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AutomationDraftReview(Base):
    __tablename__ = "automation_draft_reviews"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    draft_id: Mapped[str] = mapped_column(Text, nullable=False)
    opportunity_id: Mapped[str] = mapped_column(Text, nullable=False)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False)
    guards_json: Mapped[str] = mapped_column(Text, nullable=False)
    input_schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    output_schema_json: Mapped[str] = mapped_column(Text, nullable=False)
    test_cases_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    skill_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    skill_version_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AutomationDraft(Base):
    __tablename__ = "automation_drafts"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    opportunity_id: Mapped[str] = mapped_column(Text, nullable=False)
    scan_id: Mapped[str] = mapped_column(Text, nullable=False)
    snapshot_id: Mapped[str] = mapped_column(Text, nullable=False)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    runtime_mode: Mapped[str] = mapped_column(Text, nullable=False)
    write_actions: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    draft_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
