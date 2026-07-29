from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.canonical.enums import ERPType, InvariantSeverity, InvariantStatus
from erpguard.core.results import PreflightResult
from erpguard.db.models import (
    AuditEvent,
    AutomationDraft,
    AutomationDraftReview,
    BlockedWriteEvidenceRecord,
    Connection,
    BusinessSignal,
    BusinessSnapshot,
    ExecutionRunStep,
    IdempotencyKey,
    InvariantResult,
    LiveReadEvidence,
    LiveReadExecutionRequest,
    LiveReadRun,
    OperatorSession,
    OperatorSessionEvent,
    PreflightCase,
    RecordingEvent,
    RecordingSession,
    Opportunity,
    OpportunityScan,
    Skill,
    SkillActivationGateEvaluation,
    SkillApprovalDecision,
    SkillApprovalRequest,
    SkillDryRunProof,
    SkillRun,
    SkillRunStep,
    SkillVersion,
    Tenant,
    WriteReadinessAssessment,
    WriteReadinessCertification,
    UIRecordingSession,
    UIRecordingEvent,
    UISkillDraft,
    UICompiledSkill,
    UIReplayRun,
    UIReplayStepAudit,
    UIReplayVerification,
    UIReplayFailure,
)
from erpguard.policies.results import PolicyIssue

if TYPE_CHECKING:
    pass


def create_connection(
    session: Session,
    name: str,
    erp_type: ERPType,
    config: dict,
    status: str = "created",
) -> Connection:
    # TODO: Encrypt connection secrets or move them to a dedicated secret manager.
    connection = Connection(
        id=f"conn_{uuid4().hex}",
        erp_type=erp_type.value,
        name=name,
        config_json=_to_json(config),
        status=status,
    )
    session.add(connection)
    session.commit()
    session.refresh(connection)
    return connection


def get_connection(session: Session, connection_id: str) -> Connection | None:
    return session.get(Connection, connection_id)


def create_preflight_case(
    session: Session, result: PreflightResult, connection_id: str = "fake"
) -> PreflightCase:
    case = PreflightCase(
        id=result.id,
        connection_id=connection_id,
        actor_json=_to_json(result.actor),
        action_json=_to_json(result.action),
        canonical_action=result.canonical_action.value,
        canonical_object=result.canonical_object,
        state_snapshot_json=_to_json(result.evidence.get("target", {})),
        simulation_json=_to_json(
            {
                "predicted_impact": result.predicted_impact,
                "evidence": result.evidence,
            }
        ),
        decision=result.decision.value,
        risk_level=result.risk_level.value,
        summary=result.summary,
    )
    session.add(case)
    session.commit()
    session.refresh(case)
    return case


def create_invariant_results_from_policy_issues(
    session: Session,
    preflight_case_id: str,
    issues: list[PolicyIssue],
) -> list[InvariantResult]:
    rows = [
        InvariantResult(
            id=f"inv_{uuid4().hex}",
            preflight_case_id=preflight_case_id,
            invariant_id=issue.code,
            invariant_type="business",
            status=InvariantStatus.FAILED.value,
            severity=InvariantSeverity.BLOCKING.value,
            message=issue.message,
            evidence_json=_to_json(issue.evidence),
        )
        for issue in issues
    ]
    session.add_all(rows)
    session.commit()
    for row in rows:
        session.refresh(row)
    return rows


def create_audit_event(
    session: Session, case_id: str, event_type: str, event: dict
) -> AuditEvent:
    audit_event = AuditEvent(
        id=f"audit_{uuid4().hex}",
        case_id=case_id,
        event_type=event_type,
        event_json=_to_json(event),
    )
    session.add(audit_event)
    session.commit()
    session.refresh(audit_event)
    return audit_event


def get_preflight_case(session: Session, case_id: str) -> PreflightCase | None:
    return session.get(PreflightCase, case_id)


def create_skill(
    session: Session, name: str, description: str | None, status: str = "draft"
) -> Skill:
    skill = Skill(
        id=f"skill_{uuid4().hex}",
        name=name,
        description=description,
        status=status,
    )
    session.add(skill)
    session.commit()
    session.refresh(skill)
    return skill


def get_skill(session: Session, skill_id: str) -> Skill | None:
    return session.get(Skill, skill_id)


def get_skill_version(session: Session, skill_version_id: str) -> SkillVersion | None:
    return session.get(SkillVersion, skill_version_id)


def list_skills(session: Session) -> list[Skill]:
    return list(session.query(Skill).order_by(Skill.created_at.desc()).all())


def create_skill_version(
    session: Session,
    skill_id: str,
    version: str,
    skill_package_json: str,
    runtime_type: str,
    llm_required_for_repeated_runs: bool,
) -> SkillVersion:
    skill_version = SkillVersion(
        id=f"skill_version_{uuid4().hex}",
        skill_id=skill_id,
        version=version,
        skill_package_json=skill_package_json,
        runtime_type=runtime_type,
        llm_required_for_repeated_runs=llm_required_for_repeated_runs,
    )
    session.add(skill_version)
    session.commit()
    session.refresh(skill_version)
    return skill_version


def get_latest_skill_version(session: Session, skill_id: str) -> SkillVersion | None:
    return (
        session.query(SkillVersion)
        .filter(SkillVersion.skill_id == skill_id)
        .order_by(SkillVersion.created_at.desc())
        .first()
    )


def create_skill_run(
    session: Session,
    skill_id: str,
    skill_version_id: str,
    status: str,
    input_json: str | None = None,
    output_json: str | None = None,
    decision: str | None = None,
    error_text: str | None = None,
    estimated_tokens_saved: int | None = None,
    finished_at: datetime | None = None,
) -> SkillRun:
    skill_run = SkillRun(
        id=f"skill_run_{uuid4().hex}",
        skill_id=skill_id,
        skill_version_id=skill_version_id,
        status=status,
        input_json=input_json,
        output_json=output_json,
        decision=decision,
        error_text=error_text,
        estimated_tokens_saved=estimated_tokens_saved,
        finished_at=finished_at,
    )
    session.add(skill_run)
    session.commit()
    session.refresh(skill_run)
    return skill_run


def create_skill_run_step(
    session: Session,
    skill_run_id: str,
    step_id: str,
    step_type: str,
    status: str,
    input_json: str | None = None,
    output_json: str | None = None,
    error_text: str | None = None,
) -> SkillRunStep:
    skill_run_step = SkillRunStep(
        id=f"skill_run_step_{uuid4().hex}",
        skill_run_id=skill_run_id,
        step_id=step_id,
        step_type=step_type,
        status=status,
        input_json=input_json,
        output_json=output_json,
        error_text=error_text,
    )
    session.add(skill_run_step)
    session.commit()
    session.refresh(skill_run_step)
    return skill_run_step


def finish_skill_run(
    session: Session,
    skill_run_id: str,
    status: str,
    output_json: str | None = None,
    decision: str | None = None,
    error_text: str | None = None,
    estimated_tokens_saved: int | None = None,
):
    skill_run = session.get(SkillRun, skill_run_id)
    if skill_run is None:
        return None
    skill_run.status = status
    skill_run.output_json = output_json
    skill_run.decision = decision
    skill_run.error_text = error_text
    skill_run.estimated_tokens_saved = estimated_tokens_saved
    skill_run.finished_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(skill_run)
    return skill_run


def get_skill_run(session: Session, skill_run_id: str) -> SkillRun | None:
    return session.get(SkillRun, skill_run_id)


def list_skill_run_steps(session: Session, skill_run_id: str) -> list[SkillRunStep]:
    return list(
        session.query(SkillRunStep)
        .filter(SkillRunStep.skill_run_id == skill_run_id)
        .order_by(SkillRunStep.created_at.asc())
        .all()
    )


def list_skill_runs(session: Session, skill_id: str) -> list[SkillRun]:
    return list(
        session.query(SkillRun)
        .filter(SkillRun.skill_id == skill_id)
        .order_by(SkillRun.created_at.desc(), SkillRun.finished_at.desc())
        .all()
    )


def create_recording_session(
    session: Session,
    name: str,
    description: str | None,
    erp_type: str,
    target_base_url: str,
    created_by_actor_json: str,
    status: str = "recording",
) -> RecordingSession:
    recording_session = RecordingSession(
        id=f"recording_{uuid4().hex}",
        name=name,
        description=description,
        status=status,
        erp_type=erp_type,
        target_base_url=target_base_url,
        created_by_actor_json=created_by_actor_json,
    )
    session.add(recording_session)
    session.commit()
    session.refresh(recording_session)
    return recording_session


def get_recording_session(
    session: Session, recording_session_id: str
) -> RecordingSession | None:
    return session.get(RecordingSession, recording_session_id)


def list_recording_sessions(session: Session) -> list[RecordingSession]:
    return list(
        session.query(RecordingSession)
        .order_by(RecordingSession.created_at.desc())
        .all()
    )


def add_recording_event(
    session: Session,
    recording_session_id: str,
    event_type: str,
    url: str | None = None,
    page_title: str | None = None,
    element_role: str | None = None,
    element_text: str | None = None,
    element_label: str | None = None,
    selector: str | None = None,
    input_value: str | None = None,
    before_text_snapshot: str | None = None,
    after_text_snapshot: str | None = None,
    screenshot_path: str | None = None,
    metadata_json: str | None = None,
    event_index: int | None = None,
) -> RecordingEvent:
    if event_index is None:
        event_index = (
            session.query(RecordingEvent)
            .filter(RecordingEvent.recording_session_id == recording_session_id)
            .count()
            + 1
        )
    event = RecordingEvent(
        id=f"recording_event_{uuid4().hex}",
        recording_session_id=recording_session_id,
        event_index=event_index,
        event_type=event_type,
        url=url,
        page_title=page_title,
        element_role=element_role,
        element_text=element_text,
        element_label=element_label,
        selector=selector,
        input_value=input_value,
        before_text_snapshot=before_text_snapshot,
        after_text_snapshot=after_text_snapshot,
        screenshot_path=screenshot_path,
        metadata_json=metadata_json,
    )
    session.add(event)
    session.commit()
    session.refresh(event)
    return event


def list_recording_events(
    session: Session, recording_session_id: str
) -> list[RecordingEvent]:
    return list(
        session.query(RecordingEvent)
        .filter(RecordingEvent.recording_session_id == recording_session_id)
        .order_by(RecordingEvent.event_index.asc(), RecordingEvent.created_at.asc())
        .all()
    )


def finish_recording_session(
    session: Session, recording_session_id: str, status: str = "finished"
) -> RecordingSession | None:
    recording_session = session.get(RecordingSession, recording_session_id)
    if recording_session is None:
        return None
    recording_session.status = status
    session.commit()
    session.refresh(recording_session)
    return recording_session


def _to_json(value) -> str:
    return json.dumps(value, default=str)


def create_business_snapshot(
    session: Session,
    connection_id: str,
    erp_type: str,
    snapshot_json: str,
    status: str = "ok",
    read_only_mode: bool = True,
) -> BusinessSnapshot:
    snapshot = BusinessSnapshot(
        id=f"business_snapshot_{uuid4().hex}",
        connection_id=connection_id,
        erp_type=erp_type,
        status=status,
        read_only_mode=read_only_mode,
        snapshot_json=snapshot_json,
    )
    session.add(snapshot)
    session.commit()
    session.refresh(snapshot)
    return snapshot


def get_business_snapshot(
    session: Session, snapshot_id: str
) -> BusinessSnapshot | None:
    return session.get(BusinessSnapshot, snapshot_id)


def create_business_signal(
    session: Session,
    business_snapshot_id: str,
    signal_code: str,
    title: str,
    severity: str,
    message: str,
    evidence_json: str,
    score: int = 0,
) -> BusinessSignal:
    signal = BusinessSignal(
        id=f"business_signal_{uuid4().hex}",
        business_snapshot_id=business_snapshot_id,
        signal_code=signal_code,
        title=title,
        severity=severity,
        message=message,
        evidence_json=evidence_json,
        score=score,
    )
    session.add(signal)
    session.commit()
    session.refresh(signal)
    return signal


def list_business_signals(
    session: Session, business_snapshot_id: str
) -> list[BusinessSignal]:
    return list(
        session.query(BusinessSignal)
        .filter(BusinessSignal.business_snapshot_id == business_snapshot_id)
        .order_by(BusinessSignal.created_at.asc())
        .all()
    )


def create_opportunity_scan(
    session: Session,
    business_snapshot_id: str,
    connection_id: str,
    status: str,
    summary_json: str,
) -> OpportunityScan:
    scan = OpportunityScan(
        id=f"opportunity_scan_{uuid4().hex}",
        business_snapshot_id=business_snapshot_id,
        connection_id=connection_id,
        status=status,
        summary_json=summary_json,
    )
    session.add(scan)
    session.commit()
    session.refresh(scan)
    return scan


def get_opportunity_scan(session: Session, scan_id: str) -> OpportunityScan | None:
    return session.get(OpportunityScan, scan_id)


def create_opportunity(
    session: Session,
    opportunity_scan_id: str,
    connection_id: str,
    code: str,
    title: str,
    description: str,
    recommendation: str,
    category: str,
    priority: int,
    signal_codes_json: str,
    roi_json: str,
    evidence_json: str,
    status: str,
) -> Opportunity:
    opportunity = Opportunity(
        id=f"opportunity_{uuid4().hex}",
        opportunity_scan_id=opportunity_scan_id,
        connection_id=connection_id,
        code=code,
        title=title,
        description=description,
        recommendation=recommendation,
        category=category,
        priority=priority,
        signal_codes_json=signal_codes_json,
        roi_json=roi_json,
        evidence_json=evidence_json,
        status=status,
    )
    session.add(opportunity)
    session.commit()
    session.refresh(opportunity)
    return opportunity


def get_opportunity(session: Session, opportunity_id: str) -> Opportunity | None:
    return session.get(Opportunity, opportunity_id)


def list_opportunities(session: Session, opportunity_scan_id: str) -> list[Opportunity]:
    return list(
        session.query(Opportunity)
        .filter(Opportunity.opportunity_scan_id == opportunity_scan_id)
        .order_by(Opportunity.priority.asc(), Opportunity.created_at.asc())
        .all()
    )


def create_automation_draft(
    session: Session,
    opportunity_id: str,
    scan_id: str,
    snapshot_id: str,
    connection_id: str,
    name: str,
    description: str,
    runtime_mode: str,
    write_actions: bool,
    draft_json: str,
    status: str,
) -> AutomationDraft:
    draft = AutomationDraft(
        id=f"automation_draft_{uuid4().hex}",
        opportunity_id=opportunity_id,
        scan_id=scan_id,
        snapshot_id=snapshot_id,
        connection_id=connection_id,
        name=name,
        description=description,
        status=status,
        runtime_mode=runtime_mode,
        write_actions=write_actions,
        draft_json=draft_json,
    )
    session.add(draft)
    session.commit()
    session.refresh(draft)
    return draft


def get_automation_draft(session: Session, draft_id: str) -> AutomationDraft | None:
    return session.get(AutomationDraft, draft_id)


def list_automation_drafts(
    session: Session, opportunity_id: str
) -> list[AutomationDraft]:
    return list(
        session.query(AutomationDraft)
        .filter(AutomationDraft.opportunity_id == opportunity_id)
        .order_by(AutomationDraft.created_at.desc())
        .all()
    )


def create_automation_draft_review(
    session: Session,
    draft_id: str,
    opportunity_id: str,
    connection_id: str,
    guards_json: str,
    input_schema_json: str,
    output_schema_json: str,
    test_cases_json: str,
    status: str = "ready_to_compile",
) -> AutomationDraftReview:
    review = AutomationDraftReview(
        id=f"draft_review_{uuid4().hex}",
        draft_id=draft_id,
        opportunity_id=opportunity_id,
        connection_id=connection_id,
        guards_json=guards_json,
        input_schema_json=input_schema_json,
        output_schema_json=output_schema_json,
        test_cases_json=test_cases_json,
        status=status,
    )
    session.add(review)
    session.commit()
    session.refresh(review)
    return review


def get_automation_draft_review(
    session: Session, review_id: str
) -> AutomationDraftReview | None:
    return session.get(AutomationDraftReview, review_id)


def mark_review_compiled(
    session: Session, review_id: str, skill_id: str, skill_version_id: str
) -> AutomationDraftReview | None:
    review = session.get(AutomationDraftReview, review_id)
    if review is None:
        return None
    review.status = "compiled"
    review.skill_id = skill_id
    review.skill_version_id = skill_version_id
    session.commit()
    session.refresh(review)
    return review


def list_draft_reviews(session: Session, draft_id: str) -> list[AutomationDraftReview]:
    return list(
        session.query(AutomationDraftReview)
        .filter(AutomationDraftReview.draft_id == draft_id)
        .order_by(AutomationDraftReview.created_at.desc())
        .all()
    )


def create_skill_dry_run_proof(
    session: Session,
    skill_id: str,
    skill_version_id: str,
    draft_id: str,
    review_id: str,
    status: str,
    cases_total: int,
    cases_passed: int,
    proof_json: str,
) -> SkillDryRunProof:
    proof = SkillDryRunProof(
        id=f"dry_run_proof_{uuid4().hex}",
        skill_id=skill_id,
        skill_version_id=skill_version_id,
        draft_id=draft_id,
        review_id=review_id,
        status=status,
        cases_total=cases_total,
        cases_passed=cases_passed,
        proof_json=proof_json,
    )
    session.add(proof)
    session.commit()
    session.refresh(proof)
    return proof


def get_latest_dry_run_proof_for_skill(
    session: Session, skill_id: str
) -> SkillDryRunProof | None:
    return (
        session.query(SkillDryRunProof)
        .filter(SkillDryRunProof.skill_id == skill_id)
        .order_by(SkillDryRunProof.created_at.desc())
        .first()
    )


def create_skill_approval_request(
    session: Session,
    skill_id: str,
    skill_version_id: str,
    requested_by_json: str,
    reason: str,
    context_json: str,
    status: str = "pending",
) -> SkillApprovalRequest:
    req = SkillApprovalRequest(
        id=f"approval_request_{uuid4().hex}",
        skill_id=skill_id,
        skill_version_id=skill_version_id,
        requested_by_json=requested_by_json,
        reason=reason,
        status=status,
        can_execute_real_writes=False,
        context_json=context_json,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


def get_approval_request(
    session: Session, request_id: str
) -> SkillApprovalRequest | None:
    return session.get(SkillApprovalRequest, request_id)


def get_latest_approval_request_for_skill(
    session: Session, skill_id: str
) -> SkillApprovalRequest | None:
    return (
        session.query(SkillApprovalRequest)
        .filter(SkillApprovalRequest.skill_id == skill_id)
        .order_by(SkillApprovalRequest.created_at.desc())
        .first()
    )


def update_approval_request_status(
    session: Session, request_id: str, status: str
) -> SkillApprovalRequest | None:
    req = session.get(SkillApprovalRequest, request_id)
    if req is None:
        return None
    req.status = status
    session.commit()
    session.refresh(req)
    return req


def create_skill_approval_decision(
    session: Session,
    approval_request_id: str,
    skill_id: str,
    decided_by_json: str,
    decision: str,
    reason: str,
    evidence_json: str,
) -> SkillApprovalDecision:
    dec = SkillApprovalDecision(
        id=f"approval_decision_{uuid4().hex}",
        approval_request_id=approval_request_id,
        skill_id=skill_id,
        decided_by_json=decided_by_json,
        decision=decision,
        reason=reason,
        can_execute_real_writes=False,
        approved_for_real_execution=False,
        evidence_json=evidence_json,
    )
    session.add(dec)
    session.commit()
    session.refresh(dec)
    return dec


def list_approval_decisions_for_skill(
    session: Session, skill_id: str
) -> list[SkillApprovalDecision]:
    return list(
        session.query(SkillApprovalDecision)
        .filter(SkillApprovalDecision.skill_id == skill_id)
        .order_by(SkillApprovalDecision.created_at.desc())
        .all()
    )


def create_activation_gate_evaluation(
    session: Session,
    skill_id: str,
    gate_status: str,
    can_activate: bool,
    checks_json: str,
    approval_request_id: str | None = None,
) -> SkillActivationGateEvaluation:
    ev = SkillActivationGateEvaluation(
        id=f"gate_eval_{uuid4().hex}",
        skill_id=skill_id,
        approval_request_id=approval_request_id,
        gate_status=gate_status,
        can_activate=can_activate,
        can_execute_real_writes=False,
        approved_for_real_execution=False,
        checks_json=checks_json,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def get_latest_gate_evaluation(
    session: Session, skill_id: str
) -> SkillActivationGateEvaluation | None:
    return (
        session.query(SkillActivationGateEvaluation)
        .filter(SkillActivationGateEvaluation.skill_id == skill_id)
        .order_by(SkillActivationGateEvaluation.created_at.desc())
        .first()
    )


def create_execution_run_step(
    session: Session,
    execution_run_id: str,
    step_index: int,
    step_id: str,
    step_type: str,
    status: str,
    input_json: str,
    output_json: str,
) -> ExecutionRunStep:
    step = ExecutionRunStep(
        id=f"exec_step_{uuid4().hex}",
        execution_run_id=execution_run_id,
        step_index=step_index,
        step_id=step_id,
        step_type=step_type,
        status=status,
        input_json=input_json,
        output_json=output_json,
    )
    session.add(step)
    session.commit()
    session.refresh(step)
    return step


def get_or_create_idempotency_key(
    session: Session,
    key: str,
    skill_id: str,
    execution_request_id: str,
) -> tuple[IdempotencyKey, bool]:
    existing = session.query(IdempotencyKey).filter(IdempotencyKey.key == key).first()
    if existing:
        return existing, True
    new_key = IdempotencyKey(
        id=f"idempotency_{uuid4().hex}",
        key=key,
        skill_id=skill_id,
        execution_request_id=execution_request_id,
    )
    session.add(new_key)
    session.commit()
    session.refresh(new_key)
    return new_key, False


def create_blocked_write_evidence(
    session: Session,
    execution_run_id: str,
    execution_request_id: str,
    skill_id: str,
    attempted_model: str,
    attempted_method: str,
    attempted_args_json: str,
    blocked_reason: str,
) -> BlockedWriteEvidenceRecord:
    ev = BlockedWriteEvidenceRecord(
        id=f"blocked_write_{uuid4().hex}",
        execution_run_id=execution_run_id,
        execution_request_id=execution_request_id,
        skill_id=skill_id,
        attempted_model=attempted_model,
        attempted_method=attempted_method,
        attempted_args_json=attempted_args_json,
        blocked_reason=blocked_reason,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def create_live_read_execution_request(
    session: Session,
    skill_id: str,
    skill_version_id: str,
    requested_by_json: str,
    inputs_json: str,
    idempotency_key: str,
    connection_id: str | None = None,
    approval_request_id: str | None = None,
    status: str = "pending",
) -> LiveReadExecutionRequest:
    req = LiveReadExecutionRequest(
        id=f"lr_exec_req_{uuid4().hex}",
        skill_id=skill_id,
        skill_version_id=skill_version_id,
        connection_id=connection_id,
        approval_request_id=approval_request_id,
        requested_by_json=requested_by_json,
        inputs_json=inputs_json,
        status=status,
        can_execute_real_writes=False,
        real_erp_writes_enabled=False,
        allow_real_odoo_reads=True,
        idempotency_key=idempotency_key,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


def get_live_read_execution_request(
    session: Session, request_id: str
) -> LiveReadExecutionRequest | None:
    return session.get(LiveReadExecutionRequest, request_id)


def update_live_read_execution_request_status(
    session: Session, request_id: str, status: str
) -> LiveReadExecutionRequest | None:
    req = session.get(LiveReadExecutionRequest, request_id)
    if req is None:
        return None
    req.status = status
    session.commit()
    session.refresh(req)
    return req


def list_live_read_execution_requests_for_skill(
    session: Session, skill_id: str
) -> list[LiveReadExecutionRequest]:
    return list(
        session.query(LiveReadExecutionRequest)
        .filter(LiveReadExecutionRequest.skill_id == skill_id)
        .order_by(LiveReadExecutionRequest.created_at.desc())
        .all()
    )


def create_live_read_run(
    session: Session,
    execution_request_id: str,
    skill_id: str,
    connection_id: str | None,
    status: str,
    plan_json: str,
    result_json: str,
    real_read_count: int = 0,
    blocked_write_count: int = 0,
    finished_at=None,
) -> LiveReadRun:
    run = LiveReadRun(
        id=f"lr_run_{uuid4().hex}",
        execution_request_id=execution_request_id,
        skill_id=skill_id,
        connection_id=connection_id,
        status=status,
        plan_json=plan_json,
        result_json=result_json,
        can_execute_real_writes=False,
        real_erp_writes_enabled=False,
        allow_real_odoo_reads=True,
        real_read_count=real_read_count,
        blocked_write_count=blocked_write_count,
        finished_at=finished_at,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_live_read_run(session: Session, run_id: str) -> LiveReadRun | None:
    return session.get(LiveReadRun, run_id)


def create_live_read_evidence(
    session: Session,
    live_read_run_id: str,
    execution_request_id: str,
    skill_id: str,
    step_id: str,
    odoo_model: str,
    odoo_method: str,
    query_summary_json: str,
    records_fetched: int,
    result_summary_json: str,
) -> LiveReadEvidence:
    ev = LiveReadEvidence(
        id=f"lr_evidence_{uuid4().hex}",
        live_read_run_id=live_read_run_id,
        execution_request_id=execution_request_id,
        skill_id=skill_id,
        step_id=step_id,
        odoo_model=odoo_model,
        odoo_method=odoo_method,
        query_summary_json=query_summary_json,
        records_fetched=records_fetched,
        result_summary_json=result_summary_json,
        read_only=True,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def create_write_readiness_assessment(
    session: Session,
    skill_id: str,
    skill_version_id: str,
    status: str,
    write_candidates_json: str,
    risk_matrix_json: str,
    overall_risk_level: str,
    can_certify_write_readiness: bool,
    blocking_issues_json: str,
    permission_preview_json: str,
) -> WriteReadinessAssessment:
    row = WriteReadinessAssessment(
        id=f"write_assessment_{uuid4().hex}",
        skill_id=skill_id,
        skill_version_id=skill_version_id,
        status=status,
        write_candidates_json=write_candidates_json,
        risk_matrix_json=risk_matrix_json,
        overall_risk_level=overall_risk_level,
        can_certify_write_readiness=can_certify_write_readiness,
        blocking_issues_json=blocking_issues_json,
        permission_preview_json=permission_preview_json,
        can_execute_real_writes=False,
        real_erp_writes_enabled=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_write_readiness_assessment(
    session: Session, assessment_id: str
) -> WriteReadinessAssessment | None:
    return session.get(WriteReadinessAssessment, assessment_id)


def get_latest_write_readiness_certification_for_skill(
    session: Session, skill_id: str
) -> WriteReadinessCertification | None:
    return (
        session.query(WriteReadinessCertification)
        .filter(WriteReadinessCertification.skill_id == skill_id)
        .order_by(WriteReadinessCertification.created_at.desc())
        .first()
    )


# Sprint 8 — Write Pilot


def create_tenant(
    session: Session,
    name: str,
    environment: str,
    kill_switch_json: str,
    rate_limit_json: str,
    roles_json: str,
    secret_scope_json: str,
) -> Tenant:
    row = Tenant(
        id=f"tenant_{uuid4().hex}",
        name=name,
        environment=environment,
        status="active",
        kill_switch_json=kill_switch_json,
        rate_limit_json=rate_limit_json,
        roles_json=roles_json,
        secret_scope_json=secret_scope_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_tenant(session: Session, tenant_id: str) -> Tenant | None:
    return session.get(Tenant, tenant_id)


def list_tenants(session: Session) -> list[Tenant]:
    return list(session.query(Tenant).order_by(Tenant.created_at.desc()).all())


def suspend_tenant(session: Session, tenant_id: str) -> Tenant | None:
    row = session.get(Tenant, tenant_id)
    if row is None:
        return None
    row.status = "suspended"
    session.commit()
    session.refresh(row)
    return row


def create_operator_session(
    session: Session,
    *,
    tenant_id: str | None = None,
    connection_id: str | None = None,
    current_step: str = "awaiting_tenant",
    status: str = "active",
    known_ids_json: str = "{}",
) -> OperatorSession:
    row = OperatorSession(
        id=f"opsession_{uuid4().hex[:12]}",
        tenant_id=tenant_id,
        connection_id=connection_id,
        current_step=current_step,
        status=status,
        known_ids_json=known_ids_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_operator_session(session: Session, session_id: str) -> OperatorSession | None:
    return session.get(OperatorSession, session_id)


def update_operator_session(
    session: Session,
    session_id: str,
    *,
    tenant_id: str | None = None,
    connection_id: str | None = None,
    current_step: str | None = None,
    status: str | None = None,
    known_ids_json: str | None = None,
) -> OperatorSession | None:
    row = session.get(OperatorSession, session_id)
    if row is None:
        return None
    if tenant_id is not None:
        row.tenant_id = tenant_id
    if connection_id is not None:
        row.connection_id = connection_id
    if current_step is not None:
        row.current_step = current_step
    if status is not None:
        row.status = status
    if known_ids_json is not None:
        row.known_ids_json = known_ids_json
    session.commit()
    session.refresh(row)
    return row


def create_operator_session_event(
    session: Session,
    *,
    session_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> OperatorSessionEvent:
    row = OperatorSessionEvent(
        id=f"opev_{uuid4().hex[:12]}",
        session_id=session_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def create_ui_recording_session(
    session: Session,
    *,
    name: str,
    description: str | None = None,
    target_base_url: str,
) -> UIRecordingSession:
    row = UIRecordingSession(
        id=f"ui_session_{uuid4().hex[:16]}",
        name=name,
        description=description,
        target_base_url=target_base_url,
        status="recording",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_ui_recording_session(
    session: Session, session_id: str
) -> UIRecordingSession | None:
    return session.get(UIRecordingSession, session_id)


def finish_ui_recording_session(
    session: Session, session_id: str
) -> UIRecordingSession | None:
    row = session.get(UIRecordingSession, session_id)
    if row is None:
        return None
    row.status = "finished"
    session.commit()
    session.refresh(row)
    return row


def add_ui_recording_event(
    session: Session,
    *,
    session_id: str,
    event_type: str,
    url: str | None = None,
    selector: str | None = None,
    element_text: str | None = None,
    element_label: str | None = None,
    input_value: str | None = None,
    metadata_json: str = "{}",
) -> UIRecordingEvent:
    count = (
        session.query(UIRecordingEvent)
        .filter(UIRecordingEvent.session_id == session_id)
        .count()
    )
    row = UIRecordingEvent(
        id=f"ui_ev_{uuid4().hex[:16]}",
        session_id=session_id,
        event_index=count,
        event_type=event_type,
        url=url,
        selector=selector,
        element_text=element_text,
        element_label=element_label,
        input_value=input_value,
        metadata_json=metadata_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_ui_recording_events(
    session: Session, session_id: str
) -> list[UIRecordingEvent]:
    return list(
        session.query(UIRecordingEvent)
        .filter(UIRecordingEvent.session_id == session_id)
        .order_by(UIRecordingEvent.event_index.asc())
        .all()
    )


def create_ui_skill_draft(
    session: Session,
    *,
    session_id: str,
    name: str,
    description: str | None = None,
    steps_json: str = "[]",
    selector_map_json: str = "{}",
    guard_names_json: str = "[]",
) -> UISkillDraft:
    row = UISkillDraft(
        id=f"ui_draft_{uuid4().hex[:16]}",
        session_id=session_id,
        name=name,
        description=description,
        steps_json=steps_json,
        selector_map_json=selector_map_json,
        guard_names_json=guard_names_json,
        status="draft",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_ui_skill_draft(session: Session, draft_id: str) -> UISkillDraft | None:
    return session.get(UISkillDraft, draft_id)


def create_ui_compiled_skill(
    session: Session,
    *,
    draft_id: str,
    session_id: str,
    name: str,
    steps_json: str = "[]",
    guard_names_json: str = "[]",
) -> UICompiledSkill:
    row = UICompiledSkill(
        id=f"ui_skill_{uuid4().hex[:16]}",
        draft_id=draft_id,
        session_id=session_id,
        name=name,
        runtime_type="deterministic_ui",
        steps_json=steps_json,
        guard_names_json=guard_names_json,
        llm_required=False,
        status="compiled",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_ui_compiled_skill(
    session: Session, compiled_skill_id: str
) -> UICompiledSkill | None:
    return session.get(UICompiledSkill, compiled_skill_id)


def create_ui_replay_run(
    session: Session,
    *,
    compiled_skill_id: str,
    target_base_url: str,
    step_count: int = 0,
) -> UIReplayRun:
    row = UIReplayRun(
        id=f"ui_replay_{uuid4().hex[:16]}",
        compiled_skill_id=compiled_skill_id,
        target_base_url=target_base_url,
        status="running",
        step_count=step_count,
        steps_passed=0,
        steps_failed=0,
        result_json="{}",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_ui_replay_run(session: Session, replay_id: str) -> UIReplayRun | None:
    return session.get(UIReplayRun, replay_id)


def finish_ui_replay_run(
    session: Session,
    replay_id: str,
    *,
    status: str,
    steps_passed: int,
    steps_failed: int,
    result_json: str,
) -> UIReplayRun | None:
    from datetime import datetime, timezone

    row = session.get(UIReplayRun, replay_id)
    if row is None:
        return None
    row.status = status
    row.steps_passed = steps_passed
    row.steps_failed = steps_failed
    row.result_json = result_json
    row.finished_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(row)
    return row


def add_ui_replay_step_audit(
    session: Session,
    *,
    replay_run_id: str,
    step_index: int,
    step_id: str,
    step_type: str,
    status: str,
    before_state_json: str = "{}",
    after_state_json: str = "{}",
    evidence_json: str = "{}",
    error_text: str | None = None,
) -> UIReplayStepAudit:
    row = UIReplayStepAudit(
        id=f"ui_audit_{uuid4().hex[:16]}",
        replay_run_id=replay_run_id,
        step_index=step_index,
        step_id=step_id,
        step_type=step_type,
        status=status,
        before_state_json=before_state_json,
        after_state_json=after_state_json,
        evidence_json=evidence_json,
        error_text=error_text,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_ui_replay_step_audits(
    session: Session, replay_run_id: str
) -> list[UIReplayStepAudit]:
    return list(
        session.query(UIReplayStepAudit)
        .filter(UIReplayStepAudit.replay_run_id == replay_run_id)
        .order_by(UIReplayStepAudit.step_index.asc())
        .all()
    )


# Sprint 22 — Verification and failure repositories


def add_ui_replay_verification(
    session: Session,
    *,
    replay_run_id: str,
    step_index: int,
    step_id: str,
    page_state_ok: bool = True,
    record_identity_ok: bool = True,
    selector_ambiguity_ok: bool = True,
    modal_error_ok: bool = True,
    post_state_ok: bool = True,
    overall_status: str = "passed",
    checks_json: str = "{}",
) -> UIReplayVerification:
    row = UIReplayVerification(
        id=f"ui_verif_{uuid4().hex[:16]}",
        replay_run_id=replay_run_id,
        step_index=step_index,
        step_id=step_id,
        page_state_ok=page_state_ok,
        record_identity_ok=record_identity_ok,
        selector_ambiguity_ok=selector_ambiguity_ok,
        modal_error_ok=modal_error_ok,
        post_state_ok=post_state_ok,
        overall_status=overall_status,
        checks_json=checks_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_ui_replay_verifications(
    session: Session, replay_run_id: str
) -> list[UIReplayVerification]:
    return list(
        session.query(UIReplayVerification)
        .filter(UIReplayVerification.replay_run_id == replay_run_id)
        .order_by(UIReplayVerification.step_index.asc())
        .all()
    )


def add_ui_replay_failure(
    session: Session,
    *,
    replay_run_id: str,
    step_index: int,
    step_id: str,
    failure_type: str,
    failure_detail: str = "",
    recovery_suggestion: str = "",
    severity: str = "error",
) -> UIReplayFailure:
    row = UIReplayFailure(
        id=f"ui_fail_{uuid4().hex[:16]}",
        replay_run_id=replay_run_id,
        step_index=step_index,
        step_id=step_id,
        failure_type=failure_type,
        failure_detail=failure_detail,
        recovery_suggestion=recovery_suggestion,
        severity=severity,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_ui_replay_failures(
    session: Session, replay_run_id: str
) -> list[UIReplayFailure]:
    return list(
        session.query(UIReplayFailure)
        .filter(UIReplayFailure.replay_run_id == replay_run_id)
        .order_by(UIReplayFailure.step_index.asc())
        .all()
    )


# Sprint 23 — Skill Versioning, Promotion & Rollback

