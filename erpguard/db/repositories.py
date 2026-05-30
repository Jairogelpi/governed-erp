import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.canonical.enums import ERPType, InvariantSeverity, InvariantStatus
from erpguard.core.results import PreflightResult
from erpguard.db.models import (
    AdvisoryProposal,
    AdvisorySession,
    AgentDraftBridgeEvent,
    AgentDraftHandoffEvent,
    AgentDraftHandoffPacket,
    AgentProposalDraftLink,
    ClarificationAnswer,
    MappingConfirmation,
    ClarificationAuditEvent,
    AuditEvent,
    AgentBuilderEvent,
    AgentBuilderSession,
    AutomationDraft,
    AutomationDraftReview,
    BlockedWriteEvidenceRecord,
    Connection,
    ConnectorAuthProfile,
    ConnectorCredentialAuditEvent,
    ConnectorSetupAuditEvent,
    ConnectorSetupSession,
    ConnectorReadEvidence,
    ExternalConnectorAuditEvent,
    OAuthState,
    OAuthTokenRecord,
    BusinessSignal,
    BusinessSnapshot,
    ExecutionRequest,
    ExecutionRun,
    ExecutionRunStep,
    IdempotencyKey,
    InvariantResult,
    LiveReadEvidence,
    LiveReadExecutionRequest,
    LiveReadRun,
    OperatorSession,
    OperatorSessionEvent,
    PreflightCase,
    R2EvidenceReview,
    R2ExecutionReport,
    R2PromotionGate,
    R2RollbackRehearsal,
    R2WritePilotEvidence,
    R2WritePilotRequest,
    R2WritePilotRun,
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
    AuditExport,
    KillSwitchEvent,
    PlatformAuditEvent,
    Tenant,
    WriteImpactPreview,
    WritePilotEvidence,
    WritePilotRequest,
    WritePilotRun,
    WriteReadinessAssessment,
    WriteReadinessCertification,
    WriteRollbackPlan,
    UIRecordingSession,
    UIRecordingEvent,
    UISkillDraft,
    UICompiledSkill,
    UIReplayRun,
    UIReplayStepAudit,
    UIReplayVerification,
    UIReplayFailure,
    UISkillVersionRecord,
    UISkillVersionLifecycleEvent,
    ActiveSkillRun,
    ActiveSkillRunEvent,
    SkillSchedule,
    SkillScheduleEvent,
    SkillRunQueueEntry,
    OperatorEvidencePack,
    OperatorConsoleSession,
    OperatorConsoleQuery,
    OperatorActionPlanEvent,
    ActionPlanStepToken,
    ActionDispatchEligibilityEvent,
    ActionDispatchResultRecord,
    ActionDispatchExecutionAuditEvent,
    ManualDryRunEvidence,
    ManualDryRunAuditEvent,
    FakeERPExecutionRecord,
    FakeERPExecutionEvidence,
    FakeERPExecutionAuditEvent,
    FakeERPExecutionEvidencePack,
    FakeERPRegressionAuditEvent,
    FakeERPRegressionCase,
    FakeERPRegressionRun,
    CredentialVaultEntry,
    CredentialVaultAuditEvent,
    ERPFingerprintingPlan,
    ERPFingerprintingAuditEvent,
    SafeDiscoveryPlan,
    SafeDiscoveryAuditEvent,
    GeneratedCapabilitySet,
    GeneratedCapabilityAuditEvent,
    ReadOnlyConnectorActivationRequest,
    ReadOnlyConnectorActivation,
    ReadOnlyConnectorActivationAuditEvent,
    OdooReadOnlyAdapterSession,
    OdooReadOnlyAdapterAuditEvent,
    OdooConnectionTest,
    OdooConnectionTestAuditEvent,
    OdooReadMapping,
    OdooReadMappingAuditEvent,
    OdooReadEvidencePack,
    OdooReadEvidenceAuditEvent,
)
from erpguard.policies.results import PolicyIssue


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


def list_connections(session: Session) -> list[Connection]:
    return list(session.query(Connection).order_by(Connection.created_at.desc()).all())


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


def list_invariant_results(session: Session, case_id: str) -> list[InvariantResult]:
    return list(
        session.query(InvariantResult)
        .filter(InvariantResult.preflight_case_id == case_id)
        .order_by(InvariantResult.created_at.asc())
        .all()
    )


def list_audit_events(session: Session, case_id: str) -> list[AuditEvent]:
    return list(
        session.query(AuditEvent)
        .filter(AuditEvent.case_id == case_id)
        .order_by(AuditEvent.created_at.asc())
        .all()
    )


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


def create_agent_builder_session(
    session: Session, created_by_actor_json: str
) -> AgentBuilderSession:
    row = AgentBuilderSession(
        id=f"builder_{uuid4().hex}",
        status="created",
        trigger_json="{}",
        inputs_json="{}",
        outputs_json="{}",
        steps_json="[]",
        guards_json="[]",
        requirement_result_json="{}",
        safety_preview_json="{}",
        created_by_actor_json=created_by_actor_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_agent_builder_session(
    session: Session, session_id: str
) -> AgentBuilderSession | None:
    return session.get(AgentBuilderSession, session_id)


def update_agent_builder_session(
    session: Session, session_id: str, **updates
) -> AgentBuilderSession | None:
    row = session.get(AgentBuilderSession, session_id)
    if row is None:
        return None
    for key, value in updates.items():
        setattr(row, key, value)
    session.commit()
    session.refresh(row)
    return row


def create_agent_builder_event(
    session: Session,
    session_id: str,
    event_type: str,
    status: str,
    input_json: str = "{}",
    output_json: str = "{}",
    error_json: str = "{}",
) -> AgentBuilderEvent:
    row = AgentBuilderEvent(
        id=f"builder_event_{uuid4().hex}",
        session_id=session_id,
        event_type=event_type,
        status=status,
        input_json=input_json,
        output_json=output_json,
        error_json=error_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_builder_events(
    session: Session, session_id: str
) -> list[AgentBuilderEvent]:
    return list(
        session.query(AgentBuilderEvent)
        .filter(AgentBuilderEvent.session_id == session_id)
        .order_by(AgentBuilderEvent.created_at.asc())
        .all()
    )


def create_connector_auth_profile(
    session: Session,
    *,
    connector_id: str,
    display_name: str,
    auth_type: str,
    requested_scopes_json: str,
    credential_ref: str,
    secret_fingerprint: str,
    created_by_actor_json: str,
    oauth_readiness_json: str,
    status: str = "active",
) -> ConnectorAuthProfile:
    row = ConnectorAuthProfile(
        id=f"auth_profile_{uuid4().hex[:16]}",
        connector_id=connector_id,
        display_name=display_name,
        auth_type=auth_type,
        status=status,
        requested_scopes_json=requested_scopes_json,
        credential_ref=credential_ref,
        secret_fingerprint=secret_fingerprint,
        created_by_actor_json=created_by_actor_json,
        oauth_readiness_json=oauth_readiness_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_connector_auth_profile(
    session: Session, profile_id: str
) -> ConnectorAuthProfile | None:
    return session.get(ConnectorAuthProfile, profile_id)


def list_connector_auth_profiles(session: Session) -> list[ConnectorAuthProfile]:
    return list(
        session.query(ConnectorAuthProfile)
        .order_by(ConnectorAuthProfile.created_at.desc())
        .all()
    )


def update_connector_auth_profile(
    session: Session, profile_id: str, **updates
) -> ConnectorAuthProfile | None:
    row = session.get(ConnectorAuthProfile, profile_id)
    if row is None:
        return None
    for key, value in updates.items():
        setattr(row, key, value)
    session.commit()
    session.refresh(row)
    return row


def create_connector_credential_audit_event(
    session: Session,
    *,
    profile_id: str,
    event_type: str,
    status: str,
    actor_json: str,
    details_json: str,
) -> ConnectorCredentialAuditEvent:
    row = ConnectorCredentialAuditEvent(
        id=f"credential_audit_{uuid4().hex[:16]}",
        profile_id=profile_id,
        event_type=event_type,
        status=status,
        actor_json=actor_json,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_connector_credential_audit_events(
    session: Session, profile_id: str
) -> list[ConnectorCredentialAuditEvent]:
    return list(
        session.query(ConnectorCredentialAuditEvent)
        .filter(ConnectorCredentialAuditEvent.profile_id == profile_id)
        .order_by(ConnectorCredentialAuditEvent.created_at.asc())
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


def get_skill_dry_run_proof(session: Session, proof_id: str) -> SkillDryRunProof | None:
    return session.get(SkillDryRunProof, proof_id)


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


def list_approval_requests_for_skill(
    session: Session, skill_id: str
) -> list[SkillApprovalRequest]:
    return list(
        session.query(SkillApprovalRequest)
        .filter(SkillApprovalRequest.skill_id == skill_id)
        .order_by(SkillApprovalRequest.created_at.desc())
        .all()
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


def list_approval_decisions_for_request(
    session: Session, approval_request_id: str
) -> list[SkillApprovalDecision]:
    return list(
        session.query(SkillApprovalDecision)
        .filter(SkillApprovalDecision.approval_request_id == approval_request_id)
        .order_by(SkillApprovalDecision.created_at.desc())
        .all()
    )


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


def list_gate_evaluations_for_skill(
    session: Session, skill_id: str
) -> list[SkillActivationGateEvaluation]:
    return list(
        session.query(SkillActivationGateEvaluation)
        .filter(SkillActivationGateEvaluation.skill_id == skill_id)
        .order_by(SkillActivationGateEvaluation.created_at.desc())
        .all()
    )


def create_execution_request(
    session: Session,
    skill_id: str,
    skill_version_id: str,
    requested_by_json: str,
    inputs_json: str,
    idempotency_key: str,
    approval_request_id: str | None = None,
    status: str = "pending",
) -> ExecutionRequest:
    req = ExecutionRequest(
        id=f"execution_request_{uuid4().hex}",
        skill_id=skill_id,
        skill_version_id=skill_version_id,
        approval_request_id=approval_request_id,
        requested_by_json=requested_by_json,
        inputs_json=inputs_json,
        status=status,
        can_execute_real_writes=False,
        real_erp_writes_enabled=False,
        idempotency_key=idempotency_key,
    )
    session.add(req)
    session.commit()
    session.refresh(req)
    return req


def get_execution_request(session: Session, request_id: str) -> ExecutionRequest | None:
    return session.get(ExecutionRequest, request_id)


def update_execution_request_status(
    session: Session, request_id: str, status: str
) -> ExecutionRequest | None:
    req = session.get(ExecutionRequest, request_id)
    if req is None:
        return None
    req.status = status
    session.commit()
    session.refresh(req)
    return req


def list_execution_requests_for_skill(
    session: Session, skill_id: str
) -> list[ExecutionRequest]:
    return list(
        session.query(ExecutionRequest)
        .filter(ExecutionRequest.skill_id == skill_id)
        .order_by(ExecutionRequest.created_at.desc())
        .all()
    )


def create_execution_run(
    session: Session,
    execution_request_id: str,
    skill_id: str,
    status: str,
    plan_json: str,
    result_json: str,
    blocked_write_count: int = 0,
    finished_at=None,
) -> ExecutionRun:
    run = ExecutionRun(
        id=f"execution_run_{uuid4().hex}",
        execution_request_id=execution_request_id,
        skill_id=skill_id,
        status=status,
        plan_json=plan_json,
        result_json=result_json,
        can_execute_real_writes=False,
        real_erp_writes_enabled=False,
        blocked_write_count=blocked_write_count,
        finished_at=finished_at,
    )
    session.add(run)
    session.commit()
    session.refresh(run)
    return run


def get_execution_run(session: Session, run_id: str) -> ExecutionRun | None:
    return session.get(ExecutionRun, run_id)


def list_execution_runs_for_request(
    session: Session, execution_request_id: str
) -> list[ExecutionRun]:
    return list(
        session.query(ExecutionRun)
        .filter(ExecutionRun.execution_request_id == execution_request_id)
        .order_by(ExecutionRun.created_at.desc())
        .all()
    )


def list_execution_runs_for_skill(
    session: Session, skill_id: str
) -> list[ExecutionRun]:
    return list(
        session.query(ExecutionRun)
        .filter(ExecutionRun.skill_id == skill_id)
        .order_by(ExecutionRun.created_at.desc())
        .all()
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


def list_execution_run_steps(
    session: Session, execution_run_id: str
) -> list[ExecutionRunStep]:
    return list(
        session.query(ExecutionRunStep)
        .filter(ExecutionRunStep.execution_run_id == execution_run_id)
        .order_by(ExecutionRunStep.step_index.asc())
        .all()
    )


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


def list_blocked_write_evidence_for_run(
    session: Session, execution_run_id: str
) -> list[BlockedWriteEvidenceRecord]:
    return list(
        session.query(BlockedWriteEvidenceRecord)
        .filter(BlockedWriteEvidenceRecord.execution_run_id == execution_run_id)
        .order_by(BlockedWriteEvidenceRecord.created_at.asc())
        .all()
    )


# Sprint 6 — Live Read Execution


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


def list_live_read_runs_for_request(
    session: Session, execution_request_id: str
) -> list[LiveReadRun]:
    return list(
        session.query(LiveReadRun)
        .filter(LiveReadRun.execution_request_id == execution_request_id)
        .order_by(LiveReadRun.created_at.desc())
        .all()
    )


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


def list_live_read_evidence_for_run(
    session: Session, live_read_run_id: str
) -> list[LiveReadEvidence]:
    return list(
        session.query(LiveReadEvidence)
        .filter(LiveReadEvidence.live_read_run_id == live_read_run_id)
        .order_by(LiveReadEvidence.created_at.asc())
        .all()
    )


# Sprint 7 — Write Readiness


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


def get_latest_write_readiness_assessment_for_skill(
    session: Session, skill_id: str
) -> WriteReadinessAssessment | None:
    return (
        session.query(WriteReadinessAssessment)
        .filter(WriteReadinessAssessment.skill_id == skill_id)
        .order_by(WriteReadinessAssessment.created_at.desc())
        .first()
    )


def create_write_impact_preview(
    session: Session,
    assessment_id: str,
    skill_id: str,
    impact_summary: str,
    affected_models_json: str,
    estimated_record_count: int,
    reversible: bool,
    rollback_strategy: str,
) -> WriteImpactPreview:
    row = WriteImpactPreview(
        id=f"write_impact_{uuid4().hex}",
        assessment_id=assessment_id,
        skill_id=skill_id,
        impact_summary=impact_summary,
        affected_models_json=affected_models_json,
        estimated_record_count=estimated_record_count,
        reversible=reversible,
        rollback_strategy=rollback_strategy,
        can_execute_real_writes=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_latest_write_impact_preview_for_skill(
    session: Session, skill_id: str
) -> WriteImpactPreview | None:
    return (
        session.query(WriteImpactPreview)
        .filter(WriteImpactPreview.skill_id == skill_id)
        .order_by(WriteImpactPreview.created_at.desc())
        .first()
    )


def create_write_rollback_plan(
    session: Session,
    assessment_id: str,
    skill_id: str,
    rollback_steps_json: str,
    backup_strategy: str,
    estimated_rollback_time_minutes: int,
) -> WriteRollbackPlan:
    row = WriteRollbackPlan(
        id=f"write_rollback_{uuid4().hex}",
        assessment_id=assessment_id,
        skill_id=skill_id,
        rollback_steps_json=rollback_steps_json,
        backup_strategy=backup_strategy,
        estimated_rollback_time_minutes=estimated_rollback_time_minutes,
        can_execute_real_writes=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_latest_write_rollback_plan_for_skill(
    session: Session, skill_id: str
) -> WriteRollbackPlan | None:
    return (
        session.query(WriteRollbackPlan)
        .filter(WriteRollbackPlan.skill_id == skill_id)
        .order_by(WriteRollbackPlan.created_at.desc())
        .first()
    )


def create_write_readiness_certification(
    session: Session,
    skill_id: str,
    assessment_id: str,
    certification_status: str,
    overall_risk_level: str,
    evidence_json: str,
    impact_preview_id: str | None = None,
    rollback_plan_id: str | None = None,
) -> WriteReadinessCertification:
    row = WriteReadinessCertification(
        id=f"write_cert_{uuid4().hex}",
        skill_id=skill_id,
        assessment_id=assessment_id,
        impact_preview_id=impact_preview_id,
        rollback_plan_id=rollback_plan_id,
        certification_status=certification_status,
        overall_risk_level=overall_risk_level,
        dual_approval_required=True,
        can_certify_real_execution=False,
        can_execute_real_writes=False,
        real_erp_writes_enabled=False,
        approved_for_real_execution=False,
        evidence_json=evidence_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_write_readiness_certification(
    session: Session, certification_id: str
) -> WriteReadinessCertification | None:
    return session.get(WriteReadinessCertification, certification_id)


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


def create_write_pilot_request(
    session: Session,
    skill_id: str,
    certification_id: str | None,
    requested_by_json: str,
    approver_1_json: str,
    approver_2_json: str,
    target_model: str,
    target_res_model: str,
    target_res_id: int,
    payload_json: str,
    idempotency_key: str,
) -> WritePilotRequest:
    row = WritePilotRequest(
        id=f"wp_req_{uuid4().hex}",
        skill_id=skill_id,
        certification_id=certification_id,
        requested_by_json=requested_by_json,
        approver_1_json=approver_1_json,
        approver_2_json=approver_2_json,
        target_model=target_model,
        target_res_model=target_res_model,
        target_res_id=target_res_id,
        payload_json=payload_json,
        idempotency_key=idempotency_key,
        status="pending",
        allow_r1_real_write_pilot=False,
        allow_generic_real_odoo_writes=False,
        allow_r3_r4_real_writes=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_write_pilot_request(
    session: Session, request_id: str
) -> WritePilotRequest | None:
    return session.get(WritePilotRequest, request_id)


def get_write_pilot_request_by_idempotency_key(
    session: Session, key: str
) -> WritePilotRequest | None:
    return (
        session.query(WritePilotRequest)
        .filter(WritePilotRequest.idempotency_key == key)
        .first()
    )


def list_write_pilot_requests_for_skill(
    session: Session, skill_id: str
) -> list[WritePilotRequest]:
    return list(
        session.query(WritePilotRequest)
        .filter(WritePilotRequest.skill_id == skill_id)
        .order_by(WritePilotRequest.created_at.desc())
        .all()
    )


def create_write_pilot_run(
    session: Session,
    request_id: str,
    skill_id: str,
    status: str,
    executed_action: str,
    pre_snapshot_json: str,
    post_snapshot_json: str,
    result_json: str,
    policy_passed: bool,
    allow_r1_real_write_pilot: bool,
    finished_at=None,
) -> WritePilotRun:
    row = WritePilotRun(
        id=f"wp_run_{uuid4().hex}",
        request_id=request_id,
        skill_id=skill_id,
        status=status,
        executed_action=executed_action,
        pre_snapshot_json=pre_snapshot_json,
        post_snapshot_json=post_snapshot_json,
        result_json=result_json,
        policy_passed=policy_passed,
        allow_r1_real_write_pilot=allow_r1_real_write_pilot,
        allow_generic_real_odoo_writes=False,
        allow_r3_r4_real_writes=False,
        finished_at=finished_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_write_pilot_run(session: Session, run_id: str) -> WritePilotRun | None:
    return session.get(WritePilotRun, run_id)


def get_write_pilot_run_for_request(
    session: Session, request_id: str
) -> WritePilotRun | None:
    return (
        session.query(WritePilotRun)
        .filter(WritePilotRun.request_id == request_id)
        .order_by(WritePilotRun.created_at.desc())
        .first()
    )


def create_write_pilot_evidence(
    session: Session,
    run_id: str,
    request_id: str,
    skill_id: str,
    action_taken: str,
    target_model: str,
    target_res_model: str,
    target_res_id: str,
    pre_snapshot_json: str,
    post_snapshot_json: str,
    idempotency_key: str,
    allow_r1_real_write_pilot: bool,
) -> WritePilotEvidence:
    ev = WritePilotEvidence(
        id=f"wp_ev_{uuid4().hex}",
        run_id=run_id,
        request_id=request_id,
        skill_id=skill_id,
        action_taken=action_taken,
        target_model=target_model,
        target_res_model=target_res_model,
        target_res_id=str(target_res_id),
        pre_snapshot_json=pre_snapshot_json,
        post_snapshot_json=post_snapshot_json,
        idempotency_key=idempotency_key,
        allow_r1_real_write_pilot=allow_r1_real_write_pilot,
        allow_generic_real_odoo_writes=False,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def list_write_pilot_evidence_for_run(
    session: Session, run_id: str
) -> list[WritePilotEvidence]:
    return list(
        session.query(WritePilotEvidence)
        .filter(WritePilotEvidence.run_id == run_id)
        .order_by(WritePilotEvidence.created_at.asc())
        .all()
    )


# Sprint 9 — Production Safety Hardening & Tenant Controls


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


def update_tenant_kill_switches(
    session: Session, tenant_id: str, kill_switch_json: str
) -> Tenant | None:
    row = session.get(Tenant, tenant_id)
    if row is None:
        return None
    row.kill_switch_json = kill_switch_json
    session.commit()
    session.refresh(row)
    return row


def suspend_tenant(session: Session, tenant_id: str) -> Tenant | None:
    row = session.get(Tenant, tenant_id)
    if row is None:
        return None
    row.status = "suspended"
    session.commit()
    session.refresh(row)
    return row


def create_kill_switch_event(
    session: Session,
    tenant_id: str,
    switch_name: str,
    action: str,
    activated_by_json: str,
    reason: str,
) -> KillSwitchEvent:
    ev = KillSwitchEvent(
        id=f"ks_ev_{uuid4().hex}",
        tenant_id=tenant_id,
        switch_name=switch_name,
        action=action,
        activated_by_json=activated_by_json,
        reason=reason,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def list_kill_switch_events_for_tenant(
    session: Session, tenant_id: str
) -> list[KillSwitchEvent]:
    return list(
        session.query(KillSwitchEvent)
        .filter(KillSwitchEvent.tenant_id == tenant_id)
        .order_by(KillSwitchEvent.created_at.desc())
        .all()
    )


def create_audit_export(
    session: Session,
    tenant_id: str,
    export_type: str,
    filters_json: str,
    record_count: int,
    result_json: str,
) -> AuditExport:
    from datetime import datetime, timezone

    row = AuditExport(
        id=f"export_{uuid4().hex}",
        tenant_id=tenant_id,
        export_type=export_type,
        filters_json=filters_json,
        record_count=record_count,
        status="completed",
        result_json=result_json,
        completed_at=datetime.now(timezone.utc),
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_audit_export(session: Session, export_id: str) -> AuditExport | None:
    return session.get(AuditExport, export_id)


def create_platform_audit_event(
    session: Session,
    tenant_id: str,
    event_category: str,
    event_type: str,
    actor_json: str,
    details_json: str,
    severity: str = "info",
) -> PlatformAuditEvent:
    ev = PlatformAuditEvent(
        id=f"pae_{uuid4().hex}",
        tenant_id=tenant_id,
        event_category=event_category,
        event_type=event_type,
        actor_json=actor_json,
        details_json=details_json,
        severity=severity,
    )
    session.add(ev)
    session.commit()
    session.refresh(ev)
    return ev


def list_platform_audit_events_for_tenant(
    session: Session, tenant_id: str, limit: int = 50
) -> list[PlatformAuditEvent]:
    return list(
        session.query(PlatformAuditEvent)
        .filter(PlatformAuditEvent.tenant_id == tenant_id)
        .order_by(PlatformAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def count_write_pilot_runs_recent(session: Session, hours: int = 24) -> int:
    from datetime import datetime, timezone, timedelta
    from erpguard.db.models import WritePilotRun

    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    return (
        session.query(WritePilotRun).filter(WritePilotRun.created_at >= cutoff).count()
    )


# Sprint 10A — Operator Flow repositories


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


def list_operator_session_events(
    session: Session, session_id: str
) -> list[OperatorSessionEvent]:
    return (
        session.query(OperatorSessionEvent)
        .filter(OperatorSessionEvent.session_id == session_id)
        .order_by(OperatorSessionEvent.created_at.asc())
        .all()
    )


# Sprint 10B — R2 write pilot repositories


def create_r2_write_pilot_request(
    session: Session,
    *,
    skill_id: str,
    certification_id: str | None,
    requested_by_json: str,
    approver_1_json: str,
    approver_2_json: str,
    target_model: str,
    target_record_id: int,
    target_fields_json: str,
    vals_json: str,
    environment: str,
    idempotency_key: str,
    status: str = "pending",
    allow_r2_real_write_pilot: bool = False,
) -> R2WritePilotRequest:
    row = R2WritePilotRequest(
        id=f"r2req_{uuid4().hex[:16]}",
        skill_id=skill_id,
        certification_id=certification_id,
        requested_by_json=requested_by_json,
        approver_1_json=approver_1_json,
        approver_2_json=approver_2_json,
        target_model=target_model,
        target_record_id=target_record_id,
        target_fields_json=target_fields_json,
        vals_json=vals_json,
        environment=environment,
        idempotency_key=idempotency_key,
        status=status,
        allow_r2_real_write_pilot=allow_r2_real_write_pilot,
        allow_generic_real_odoo_writes=False,
        allow_r3_r4_real_writes=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_r2_write_pilot_request(
    session: Session, request_id: str
) -> R2WritePilotRequest | None:
    return session.get(R2WritePilotRequest, request_id)


def get_r2_write_pilot_request_by_idempotency_key(
    session: Session, key: str
) -> R2WritePilotRequest | None:
    return (
        session.query(R2WritePilotRequest)
        .filter(R2WritePilotRequest.idempotency_key == key)
        .first()
    )


def list_r2_write_pilot_requests_for_skill(
    session: Session, skill_id: str
) -> list[R2WritePilotRequest]:
    return (
        session.query(R2WritePilotRequest)
        .filter(R2WritePilotRequest.skill_id == skill_id)
        .order_by(R2WritePilotRequest.created_at.desc())
        .all()
    )


def create_r2_write_pilot_run(
    session: Session,
    *,
    request_id: str,
    skill_id: str,
    status: str,
    executed_action: str,
    pre_snapshot_json: str,
    post_snapshot_json: str,
    result_json: str,
    policy_passed: bool,
    allow_r2_real_write_pilot: bool,
    finished_at=None,
) -> R2WritePilotRun:
    row = R2WritePilotRun(
        id=f"r2run_{uuid4().hex[:16]}",
        request_id=request_id,
        skill_id=skill_id,
        status=status,
        executed_action=executed_action,
        pre_snapshot_json=pre_snapshot_json,
        post_snapshot_json=post_snapshot_json,
        result_json=result_json,
        policy_passed=policy_passed,
        allow_r2_real_write_pilot=allow_r2_real_write_pilot,
        allow_generic_real_odoo_writes=False,
        allow_r3_r4_real_writes=False,
        finished_at=finished_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_r2_write_pilot_run(session: Session, run_id: str) -> R2WritePilotRun | None:
    return session.get(R2WritePilotRun, run_id)


def get_r2_write_pilot_run_for_request(
    session: Session, request_id: str
) -> R2WritePilotRun | None:
    return (
        session.query(R2WritePilotRun)
        .filter(R2WritePilotRun.request_id == request_id)
        .first()
    )


def create_r2_write_pilot_evidence(
    session: Session,
    *,
    run_id: str,
    request_id: str,
    skill_id: str,
    action_taken: str,
    target_model: str,
    target_record_id: str,
    pre_snapshot_json: str,
    post_snapshot_json: str,
    rollback_instructions_json: str,
    idempotency_key: str,
    allow_r2_real_write_pilot: bool,
) -> R2WritePilotEvidence:
    row = R2WritePilotEvidence(
        id=f"r2ev_{uuid4().hex[:16]}",
        run_id=run_id,
        request_id=request_id,
        skill_id=skill_id,
        action_taken=action_taken,
        target_model=target_model,
        target_record_id=target_record_id,
        pre_snapshot_json=pre_snapshot_json,
        post_snapshot_json=post_snapshot_json,
        rollback_instructions_json=rollback_instructions_json,
        idempotency_key=idempotency_key,
        allow_r2_real_write_pilot=allow_r2_real_write_pilot,
        allow_generic_real_odoo_writes=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_r2_write_pilot_evidence_for_run(
    session: Session, run_id: str
) -> list[R2WritePilotEvidence]:
    return (
        session.query(R2WritePilotEvidence)
        .filter(R2WritePilotEvidence.run_id == run_id)
        .order_by(R2WritePilotEvidence.created_at.asc())
        .all()
    )


# Sprint 11 — R2 Evidence Review, Rollback Rehearsal & Production Readiness


def create_r2_evidence_review(
    session: Session,
    *,
    run_id: str,
    skill_id: str,
    delta_json: str = "{}",
    fields_changed: int = 0,
    fields_unchanged: int = 0,
    drift_detected: bool = False,
    drift_details_json: str = "[]",
    status: str = "completed",
) -> R2EvidenceReview:
    row = R2EvidenceReview(
        id=f"r2review_{uuid4().hex[:12]}",
        run_id=run_id,
        skill_id=skill_id,
        delta_json=delta_json,
        fields_changed=fields_changed,
        fields_unchanged=fields_unchanged,
        drift_detected=drift_detected,
        drift_details_json=drift_details_json,
        status=status,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_r2_evidence_review_for_run(
    session: Session, run_id: str
) -> R2EvidenceReview | None:
    return (
        session.query(R2EvidenceReview)
        .filter(R2EvidenceReview.run_id == run_id)
        .first()
    )


def create_r2_rollback_rehearsal(
    session: Session,
    *,
    run_id: str,
    skill_id: str,
    instructions_valid: bool,
    missing_fields_json: str = "[]",
    dry_run_steps_json: str = "[]",
    rehearsal_passed: bool,
    notes: str = "",
) -> R2RollbackRehearsal:
    row = R2RollbackRehearsal(
        id=f"r2reh_{uuid4().hex[:12]}",
        run_id=run_id,
        skill_id=skill_id,
        instructions_valid=instructions_valid,
        missing_fields_json=missing_fields_json,
        dry_run_steps_json=dry_run_steps_json,
        rehearsal_passed=rehearsal_passed,
        notes=notes,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_r2_rollback_rehearsal_for_run(
    session: Session, run_id: str
) -> R2RollbackRehearsal | None:
    return (
        session.query(R2RollbackRehearsal)
        .filter(R2RollbackRehearsal.run_id == run_id)
        .first()
    )


def create_r2_execution_report(
    session: Session,
    *,
    run_id: str,
    skill_id: str,
    report_json: str = "{}",
    residual_risk_score: int = 0,
    risk_level: str = "low",
    status: str = "completed",
) -> R2ExecutionReport:
    row = R2ExecutionReport(
        id=f"r2report_{uuid4().hex[:12]}",
        run_id=run_id,
        skill_id=skill_id,
        report_json=report_json,
        residual_risk_score=residual_risk_score,
        risk_level=risk_level,
        status=status,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_r2_execution_report_for_run(
    session: Session, run_id: str
) -> R2ExecutionReport | None:
    return (
        session.query(R2ExecutionReport)
        .filter(R2ExecutionReport.run_id == run_id)
        .first()
    )


def create_r2_promotion_gate(
    session: Session,
    *,
    run_id: str,
    skill_id: str,
    gate_status: str,
    blocked: bool,
    checks_json: str = "[]",
    blocking_reasons_json: str = "[]",
) -> R2PromotionGate:
    row = R2PromotionGate(
        id=f"r2gate_{uuid4().hex[:12]}",
        run_id=run_id,
        skill_id=skill_id,
        gate_status=gate_status,
        blocked=blocked,
        checks_json=checks_json,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_r2_promotion_gate_for_run(
    session: Session, run_id: str
) -> R2PromotionGate | None:
    return (
        session.query(R2PromotionGate).filter(R2PromotionGate.run_id == run_id).first()
    )


# Sprint 18 — External Connector Read-Only Pilot


def create_connector_read_evidence(
    session: Session,
    *,
    auth_profile_id: str,
    connector_id: str,
    operation: str,
    fixture_mode: bool,
    record_count: int,
    redacted_fields_count: int,
    result_summary_json: str,
    policy_passed: bool = True,
) -> ConnectorReadEvidence:
    row = ConnectorReadEvidence(
        id=f"cre_{uuid4().hex[:16]}",
        auth_profile_id=auth_profile_id,
        connector_id=connector_id,
        operation=operation,
        fixture_mode=fixture_mode,
        record_count=record_count,
        redacted_fields_count=redacted_fields_count,
        result_summary_json=result_summary_json,
        policy_passed=policy_passed,
        read_only=True,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_connector_read_evidence(
    session: Session, evidence_id: str
) -> ConnectorReadEvidence | None:
    return session.get(ConnectorReadEvidence, evidence_id)


def list_connector_read_evidence_for_profile(
    session: Session, auth_profile_id: str
) -> list[ConnectorReadEvidence]:
    return list(
        session.query(ConnectorReadEvidence)
        .filter(ConnectorReadEvidence.auth_profile_id == auth_profile_id)
        .order_by(ConnectorReadEvidence.created_at.desc())
        .all()
    )


def create_external_connector_audit_event(
    session: Session,
    *,
    auth_profile_id: str,
    connector_id: str,
    event_type: str,
    operation: str,
    status: str,
    fixture_mode: bool,
    actor_json: str,
    details_json: str,
) -> ExternalConnectorAuditEvent:
    row = ExternalConnectorAuditEvent(
        id=f"ecae_{uuid4().hex[:16]}",
        auth_profile_id=auth_profile_id,
        connector_id=connector_id,
        event_type=event_type,
        operation=operation,
        status=status,
        fixture_mode=fixture_mode,
        actor_json=actor_json,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_external_connector_audit_events_for_profile(
    session: Session, auth_profile_id: str
) -> list[ExternalConnectorAuditEvent]:
    return list(
        session.query(ExternalConnectorAuditEvent)
        .filter(ExternalConnectorAuditEvent.auth_profile_id == auth_profile_id)
        .order_by(ExternalConnectorAuditEvent.created_at.asc())
        .all()
    )


# Sprint 54 - Connector Autopilot Setup Session


def create_connector_setup_session(
    session: Session,
    *,
    session_id: str,
    connector_name: str,
    erp_url: str,
    erp_url_host: str,
    environment_type: str,
    submitted_by: str,
    status: str,
    credential_mode: str,
    credential_ref: str | None,
    detected_adapter_type: str | None,
    blocking_reasons_json: str,
) -> ConnectorSetupSession:
    row = ConnectorSetupSession(
        id=session_id,
        connector_name=connector_name,
        erp_url=erp_url,
        erp_url_host=erp_url_host,
        environment_type=environment_type,
        submitted_by=submitted_by,
        status=status,
        credential_mode=credential_mode,
        credential_ref=credential_ref,
        detected_adapter_type=detected_adapter_type,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_connector_setup_session(
    session: Session, session_id: str
) -> ConnectorSetupSession | None:
    return session.get(ConnectorSetupSession, session_id)


def list_connector_setup_sessions(session: Session) -> list[ConnectorSetupSession]:
    return list(
        session.query(ConnectorSetupSession)
        .order_by(ConnectorSetupSession.created_at.desc())
        .all()
    )


def update_connector_setup_session(
    session: Session,
    session_id: str,
    *,
    status: str | None = None,
    credential_mode: str | None = None,
    credential_ref: str | None = None,
    detected_adapter_type: str | None = None,
    blocking_reasons_json: str | None = None,
) -> ConnectorSetupSession | None:
    row = session.get(ConnectorSetupSession, session_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if credential_mode is not None:
        row.credential_mode = credential_mode
    if credential_ref is not None:
        row.credential_ref = credential_ref
    if detected_adapter_type is not None:
        row.detected_adapter_type = detected_adapter_type
    if blocking_reasons_json is not None:
        row.blocking_reasons_json = blocking_reasons_json
    session.commit()
    session.refresh(row)
    return row


def create_connector_setup_audit_event(
    session: Session,
    *,
    event_id: str,
    session_id: str,
    event_type: str,
    status: str,
    submitted_by: str,
    detail_json: str,
) -> ConnectorSetupAuditEvent:
    row = ConnectorSetupAuditEvent(
        id=event_id,
        session_id=session_id,
        event_type=event_type,
        status=status,
        submitted_by=submitted_by,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_connector_setup_audit_events(
    session: Session,
) -> list[ConnectorSetupAuditEvent]:
    return list(
        session.query(ConnectorSetupAuditEvent)
        .order_by(ConnectorSetupAuditEvent.created_at.asc())
        .all()
    )


# Sprint 19 — OAuth Consent Flow


def create_oauth_state(
    session: Session,
    *,
    state_token: str,
    profile_id: str,
    connector_id: str,
    redirect_uri: str,
    scope_requested: str,
    expires_at,
) -> OAuthState:
    row = OAuthState(
        id=f"oauth_state_{uuid4().hex[:16]}",
        state_token=state_token,
        profile_id=profile_id,
        connector_id=connector_id,
        redirect_uri=redirect_uri,
        scope_requested=scope_requested,
        status="pending",
        expires_at=expires_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_oauth_state_by_token(session: Session, state_token: str) -> OAuthState | None:
    return (
        session.query(OAuthState).filter(OAuthState.state_token == state_token).first()
    )


def consume_oauth_state(session: Session, state_token: str) -> OAuthState | None:
    from datetime import datetime, timezone

    row = (
        session.query(OAuthState).filter(OAuthState.state_token == state_token).first()
    )
    if row is None:
        return None
    row.status = "used"
    row.used_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(row)
    return row


def create_oauth_token_record(
    session: Session,
    *,
    profile_id: str,
    connector_id: str,
    vault_ref: str,
    secret_fingerprint: str,
    scope_granted_json: str,
    scope_compliant: bool,
    has_refresh_token: bool,
    token_type: str,
    placeholder_mode: bool,
    expires_at=None,
) -> OAuthTokenRecord:
    row = OAuthTokenRecord(
        id=f"oauth_token_{uuid4().hex[:16]}",
        profile_id=profile_id,
        connector_id=connector_id,
        vault_ref=vault_ref,
        secret_fingerprint=secret_fingerprint,
        scope_granted_json=scope_granted_json,
        scope_compliant=scope_compliant,
        has_refresh_token=has_refresh_token,
        token_type=token_type,
        placeholder_mode=placeholder_mode,
        status="active",
        expires_at=expires_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_oauth_token_record_for_profile(
    session: Session, profile_id: str
) -> OAuthTokenRecord | None:
    return (
        session.query(OAuthTokenRecord)
        .filter(
            OAuthTokenRecord.profile_id == profile_id,
            OAuthTokenRecord.status == "active",
        )
        .order_by(OAuthTokenRecord.created_at.desc())
        .first()
    )


def revoke_oauth_token_record(
    session: Session, profile_id: str
) -> OAuthTokenRecord | None:
    from datetime import datetime, timezone

    row = get_oauth_token_record_for_profile(session, profile_id)
    if row is None:
        return None
    row.status = "revoked"
    row.revoked_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(row)
    return row


# Sprint 20 — Record-to-Skill End-to-End Loop


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


def create_ui_skill_version_record(
    session: Session,
    *,
    skill_id: str,
    compiled_skill_id: str,
    name: str,
    steps_json: str = "[]",
    guard_names_json: str = "[]",
    replay_run_id: str | None = None,
    runtime_type: str = "deterministic_ui",
    llm_required: bool = False,
) -> UISkillVersionRecord:
    version_number = (
        session.query(UISkillVersionRecord)
        .filter(UISkillVersionRecord.skill_id == skill_id)
        .count()
    ) + 1
    row = UISkillVersionRecord(
        id=f"ui_skv_{uuid4().hex[:16]}",
        skill_id=skill_id,
        compiled_skill_id=compiled_skill_id,
        version_number=version_number,
        name=name,
        status="draft",
        steps_json=steps_json,
        guard_names_json=guard_names_json,
        replay_run_id=replay_run_id,
        promotion_readiness_json="{}",
        llm_required=llm_required,
        runtime_type=runtime_type,
        is_active=False,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_ui_skill_version_record(
    session: Session, version_id: str
) -> UISkillVersionRecord | None:
    return session.get(UISkillVersionRecord, version_id)


def list_ui_skill_version_records(
    session: Session, skill_id: str
) -> list[UISkillVersionRecord]:
    return list(
        session.query(UISkillVersionRecord)
        .filter(UISkillVersionRecord.skill_id == skill_id)
        .order_by(UISkillVersionRecord.version_number.asc())
        .all()
    )


def get_active_ui_skill_version(
    session: Session, skill_id: str
) -> UISkillVersionRecord | None:
    return (
        session.query(UISkillVersionRecord)
        .filter(
            UISkillVersionRecord.skill_id == skill_id,
            UISkillVersionRecord.is_active.is_(True),
        )
        .first()
    )


def update_ui_skill_version_status(
    session: Session,
    version_id: str,
    status: str,
    is_active: bool | None = None,
    promotion_readiness_json: str | None = None,
) -> UISkillVersionRecord | None:
    row = session.get(UISkillVersionRecord, version_id)
    if row is None:
        return None
    row.status = status
    if is_active is not None:
        row.is_active = is_active
    if promotion_readiness_json is not None:
        row.promotion_readiness_json = promotion_readiness_json
    session.commit()
    session.refresh(row)
    return row


def create_ui_skill_version_lifecycle_event(
    session: Session,
    *,
    version_id: str,
    skill_id: str,
    event_type: str,
    from_status: str,
    to_status: str,
    actor: str = "system",
    reason: str = "",
) -> UISkillVersionLifecycleEvent:
    row = UISkillVersionLifecycleEvent(
        id=f"ui_skve_{uuid4().hex[:16]}",
        version_id=version_id,
        skill_id=skill_id,
        event_type=event_type,
        from_status=from_status,
        to_status=to_status,
        actor=actor,
        reason=reason,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_ui_skill_version_lifecycle_events(
    session: Session, version_id: str
) -> list[UISkillVersionLifecycleEvent]:
    return list(
        session.query(UISkillVersionLifecycleEvent)
        .filter(UISkillVersionLifecycleEvent.version_id == version_id)
        .order_by(UISkillVersionLifecycleEvent.created_at.asc())
        .all()
    )


def list_all_ui_skill_version_records(
    session: Session,
    *,
    status_filter: str | None = None,
    runtime_type_filter: str | None = None,
    active_only: bool = False,
    limit: int = 200,
) -> list[UISkillVersionRecord]:
    q = session.query(UISkillVersionRecord)
    if status_filter:
        q = q.filter(UISkillVersionRecord.status == status_filter)
    if runtime_type_filter:
        q = q.filter(UISkillVersionRecord.runtime_type == runtime_type_filter)
    if active_only:
        q = q.filter(UISkillVersionRecord.is_active.is_(True))
    return list(q.order_by(UISkillVersionRecord.created_at.desc()).limit(limit).all())


# Sprint 24 — Active Skill Runner & Manual Runs


def create_active_skill_run(
    session: Session,
    *,
    version_id: str,
    skill_id: str,
    actor: str = "manual_operator",
    target_base_url: str,
    inputs_json: str = "{}",
    gate_result_json: str = "{}",
    input_validation_json: str = "{}",
) -> ActiveSkillRun:
    row = ActiveSkillRun(
        id=f"as_run_{uuid4().hex[:16]}",
        version_id=version_id,
        skill_id=skill_id,
        actor=actor,
        trigger="manual",
        status="requested",
        target_base_url=target_base_url,
        inputs_json=inputs_json,
        gate_result_json=gate_result_json,
        input_validation_json=input_validation_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_active_skill_run(session: Session, run_id: str) -> ActiveSkillRun | None:
    return session.get(ActiveSkillRun, run_id)


def list_active_skill_runs_for_skill(
    session: Session, skill_id: str
) -> list[ActiveSkillRun]:
    return list(
        session.query(ActiveSkillRun)
        .filter(ActiveSkillRun.skill_id == skill_id)
        .order_by(ActiveSkillRun.created_at.desc())
        .all()
    )


def update_active_skill_run(
    session: Session,
    run_id: str,
    *,
    status: str | None = None,
    replay_run_id: str | None = None,
    summary_json: str | None = None,
    finished_at=None,
) -> ActiveSkillRun | None:
    row = session.get(ActiveSkillRun, run_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if replay_run_id is not None:
        row.replay_run_id = replay_run_id
    if summary_json is not None:
        row.summary_json = summary_json
    if finished_at is not None:
        row.finished_at = finished_at
    session.commit()
    session.refresh(row)
    return row


def add_active_skill_run_event(
    session: Session,
    *,
    run_id: str,
    event_type: str,
    status: str = "info",
    detail: str = "",
    payload_json: str = "{}",
) -> ActiveSkillRunEvent:
    row = ActiveSkillRunEvent(
        id=f"as_ev_{uuid4().hex[:16]}",
        run_id=run_id,
        event_type=event_type,
        status=status,
        detail=detail,
        payload_json=payload_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_active_skill_run_events(
    session: Session, run_id: str
) -> list[ActiveSkillRunEvent]:
    return list(
        session.query(ActiveSkillRunEvent)
        .filter(ActiveSkillRunEvent.run_id == run_id)
        .order_by(ActiveSkillRunEvent.created_at.asc())
        .all()
    )


# Sprint 25 — Scheduled Skill Runs & Run Queue Safety


def create_skill_schedule(
    session: Session,
    *,
    version_id: str,
    skill_id: str,
    name: str,
    interval_seconds: int,
    min_interval_seconds: int = 60,
    dedup_window_seconds: int = 30,
    target_base_url: str,
    inputs_json: str = "{}",
    created_by: str = "manual_operator",
) -> SkillSchedule:
    row = SkillSchedule(
        id=f"sch_{uuid4().hex[:16]}",
        version_id=version_id,
        skill_id=skill_id,
        name=name,
        interval_seconds=interval_seconds,
        min_interval_seconds=min_interval_seconds,
        dedup_window_seconds=dedup_window_seconds,
        status="draft",
        target_base_url=target_base_url,
        inputs_json=inputs_json,
        created_by=created_by,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_skill_schedule(session: Session, schedule_id: str) -> SkillSchedule | None:
    return session.get(SkillSchedule, schedule_id)


def list_skill_schedules_for_skill(
    session: Session, skill_id: str
) -> list[SkillSchedule]:
    return list(
        session.query(SkillSchedule)
        .filter(SkillSchedule.skill_id == skill_id)
        .order_by(SkillSchedule.created_at.asc())
        .all()
    )


def list_due_active_skill_schedules(session: Session, now) -> list[SkillSchedule]:
    return list(
        session.query(SkillSchedule)
        .filter(
            SkillSchedule.status == "active",
            SkillSchedule.next_run_at.is_not(None),
            SkillSchedule.next_run_at <= now,
        )
        .order_by(SkillSchedule.next_run_at.asc())
        .all()
    )


_UNSET = object()


def update_skill_schedule(
    session: Session,
    schedule_id: str,
    *,
    status: str | None = None,
    next_run_at=_UNSET,
    last_run_at=_UNSET,
    last_run_id: str | None = None,
    inputs_json: str | None = None,
    tick_lock_token=_UNSET,
    tick_lock_until=_UNSET,
) -> SkillSchedule | None:
    row = session.get(SkillSchedule, schedule_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if next_run_at is not _UNSET:
        row.next_run_at = next_run_at
    if last_run_at is not _UNSET:
        row.last_run_at = last_run_at
    if last_run_id is not None:
        row.last_run_id = last_run_id
    if inputs_json is not None:
        row.inputs_json = inputs_json
    if tick_lock_token is not _UNSET:
        row.tick_lock_token = tick_lock_token
    if tick_lock_until is not _UNSET:
        row.tick_lock_until = tick_lock_until
    session.commit()
    session.refresh(row)
    return row


def add_skill_schedule_event(
    session: Session,
    *,
    schedule_id: str,
    event_type: str,
    status: str = "info",
    detail: str = "",
    payload_json: str = "{}",
) -> SkillScheduleEvent:
    row = SkillScheduleEvent(
        id=f"sch_ev_{uuid4().hex[:16]}",
        schedule_id=schedule_id,
        event_type=event_type,
        status=status,
        detail=detail,
        payload_json=payload_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_skill_schedule_events(
    session: Session, schedule_id: str
) -> list[SkillScheduleEvent]:
    return list(
        session.query(SkillScheduleEvent)
        .filter(SkillScheduleEvent.schedule_id == schedule_id)
        .order_by(SkillScheduleEvent.created_at.asc())
        .all()
    )


def create_skill_run_queue_entry(
    session: Session,
    *,
    schedule_id: str,
    version_id: str,
    skill_id: str,
    inputs_json: str,
    target_base_url: str,
    status: str = "queued",
    detail: str = "",
) -> SkillRunQueueEntry:
    row = SkillRunQueueEntry(
        id=f"q_{uuid4().hex[:16]}",
        schedule_id=schedule_id,
        version_id=version_id,
        skill_id=skill_id,
        status=status,
        inputs_json=inputs_json,
        target_base_url=target_base_url,
        detail=detail,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_skill_run_queue_entry(
    session: Session, entry_id: str
) -> SkillRunQueueEntry | None:
    return session.get(SkillRunQueueEntry, entry_id)


def list_skill_run_queue_entries_for_schedule(
    session: Session, schedule_id: str
) -> list[SkillRunQueueEntry]:
    return list(
        session.query(SkillRunQueueEntry)
        .filter(SkillRunQueueEntry.schedule_id == schedule_id)
        .order_by(SkillRunQueueEntry.enqueued_at.desc())
        .all()
    )


def list_recent_queue_entries_for_schedule(
    session: Session,
    schedule_id: str,
    since,
) -> list[SkillRunQueueEntry]:
    return list(
        session.query(SkillRunQueueEntry)
        .filter(
            SkillRunQueueEntry.schedule_id == schedule_id,
            SkillRunQueueEntry.enqueued_at >= since,
        )
        .order_by(SkillRunQueueEntry.enqueued_at.desc())
        .all()
    )


def update_skill_run_queue_entry(
    session: Session,
    entry_id: str,
    *,
    status: str | None = None,
    run_id: str | None = None,
    detail: str | None = None,
    dispatched_at=None,
    finished_at=None,
) -> SkillRunQueueEntry | None:
    row = session.get(SkillRunQueueEntry, entry_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if run_id is not None:
        row.run_id = run_id
    if detail is not None:
        row.detail = detail
    if dispatched_at is not None:
        row.dispatched_at = dispatched_at
    if finished_at is not None:
        row.finished_at = finished_at
    session.commit()
    session.refresh(row)
    return row


# Sprint 26 — Operator Evidence Packs


def create_operator_evidence_pack(
    session: Session,
    created_by: str,
    scenario_label: str,
    sprint_chain: str,
    seed_result: dict,
    safety_checks: dict,
    runbook_summary: dict,
    test_evidence: dict,
    evidence_status: str = "assembling",
) -> OperatorEvidencePack:
    pack = OperatorEvidencePack(
        id=f"evpack_{uuid4().hex[:12]}",
        created_by=created_by,
        scenario_label=scenario_label,
        sprint_chain=sprint_chain,
        seed_result_json=json.dumps(seed_result),
        safety_checks_json=json.dumps(safety_checks),
        runbook_summary_json=json.dumps(runbook_summary),
        test_evidence_json=json.dumps(test_evidence),
        evidence_status=evidence_status,
    )
    session.add(pack)
    session.commit()
    session.refresh(pack)
    return pack


def get_operator_evidence_pack(
    session: Session, pack_id: str
) -> OperatorEvidencePack | None:
    return session.get(OperatorEvidencePack, pack_id)


def list_operator_evidence_packs(session: Session) -> list[OperatorEvidencePack]:
    return list(
        session.query(OperatorEvidencePack)
        .order_by(OperatorEvidencePack.created_at.desc())
        .all()
    )


# Sprint 28 — Conversational Agent Builder Advisory Mode


def create_advisory_session(
    session: Session, created_by_actor_json: str
) -> AdvisorySession:
    row = AdvisorySession(
        id=f"advisory_{uuid4().hex}",
        status="created",
        request_text="",
        created_by_actor_json=created_by_actor_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_advisory_session(session: Session, session_id: str) -> AdvisorySession | None:
    return session.get(AdvisorySession, session_id)


def update_advisory_session(
    session: Session, session_id: str, **updates
) -> AdvisorySession | None:
    row = session.get(AdvisorySession, session_id)
    if row is None:
        return None
    for key, value in updates.items():
        setattr(row, key, value)
    session.commit()
    session.refresh(row)
    return row


def create_advisory_proposal(
    session: Session,
    session_id: str,
    request_text: str,
    intent_json: str = "{}",
    process_category: str = "unknown",
    entity_mappings_json: str = "[]",
    workflow_json: str = "{}",
    guards_json: str = "{}",
    risk_summary_json: str = "{}",
    clarification_questions_json: str = "[]",
    revision_number: int = 1,
    status: str = "draft",
) -> AdvisoryProposal:
    row = AdvisoryProposal(
        id=f"proposal_{uuid4().hex}",
        session_id=session_id,
        request_text=request_text,
        intent_json=intent_json,
        process_category=process_category,
        entity_mappings_json=entity_mappings_json,
        workflow_json=workflow_json,
        guards_json=guards_json,
        risk_summary_json=risk_summary_json,
        clarification_questions_json=clarification_questions_json,
        revision_number=revision_number,
        status=status,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_advisory_proposal(
    session: Session, proposal_id: str
) -> AdvisoryProposal | None:
    return session.get(AdvisoryProposal, proposal_id)


def update_advisory_proposal(
    session: Session, proposal_id: str, **updates
) -> AdvisoryProposal | None:
    row = session.get(AdvisoryProposal, proposal_id)
    if row is None:
        return None
    for key, value in updates.items():
        setattr(row, key, value)
    session.commit()
    session.refresh(row)
    return row


def list_advisory_proposals_for_session(
    session: Session, session_id: str
) -> list[AdvisoryProposal]:
    return list(
        session.query(AdvisoryProposal)
        .filter(AdvisoryProposal.session_id == session_id)
        .order_by(AdvisoryProposal.created_at.asc())
        .all()
    )


# Sprint 29 — Agent Proposal to AutomationDraft


def create_agent_proposal_draft_link(
    session: Session,
    proposal_id: str,
    draft_id: str,
    session_id: str,
) -> AgentProposalDraftLink:
    link = AgentProposalDraftLink(
        id=f"pdlink_{uuid4().hex[:16]}",
        proposal_id=proposal_id,
        draft_id=draft_id,
        session_id=session_id,
    )
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def get_agent_proposal_draft_link_by_proposal(
    session: Session, proposal_id: str
) -> AgentProposalDraftLink | None:
    return (
        session.query(AgentProposalDraftLink)
        .filter(AgentProposalDraftLink.proposal_id == proposal_id)
        .order_by(AgentProposalDraftLink.created_at.desc())
        .first()
    )


def get_agent_proposal_draft_link_by_draft(
    session: Session, draft_id: str
) -> AgentProposalDraftLink | None:
    return (
        session.query(AgentProposalDraftLink)
        .filter(AgentProposalDraftLink.draft_id == draft_id)
        .order_by(AgentProposalDraftLink.created_at.desc())
        .first()
    )


# Sprint 30 — Agent Clarification Loop & Mapping Confirmation


def create_clarification_answer(
    session: Session,
    proposal_id: str,
    question_id: str,
    answer_text: str,
) -> ClarificationAnswer:
    row = ClarificationAnswer(
        id=f"clarif_ans_{uuid4().hex[:16]}",
        proposal_id=proposal_id,
        question_id=question_id,
        answer_text=answer_text,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_clarification_answers_for_proposal(
    session: Session, proposal_id: str
) -> list[ClarificationAnswer]:
    return list(
        session.query(ClarificationAnswer)
        .filter(ClarificationAnswer.proposal_id == proposal_id)
        .order_by(ClarificationAnswer.created_at.asc())
        .all()
    )


def get_latest_clarification_answer_for_question(
    session: Session, proposal_id: str, question_id: str
) -> ClarificationAnswer | None:
    return (
        session.query(ClarificationAnswer)
        .filter(
            ClarificationAnswer.proposal_id == proposal_id,
            ClarificationAnswer.question_id == question_id,
        )
        .order_by(ClarificationAnswer.created_at.desc())
        .first()
    )


def create_mapping_confirmation(
    session: Session,
    proposal_id: str,
    mapping_key: str,
    action: str,
    reason: str | None = None,
) -> MappingConfirmation:
    row = MappingConfirmation(
        id=f"map_conf_{uuid4().hex[:16]}",
        proposal_id=proposal_id,
        mapping_key=mapping_key,
        action=action,
        reason=reason,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_mapping_confirmations_for_proposal(
    session: Session, proposal_id: str
) -> list[MappingConfirmation]:
    return list(
        session.query(MappingConfirmation)
        .filter(MappingConfirmation.proposal_id == proposal_id)
        .order_by(MappingConfirmation.created_at.asc())
        .all()
    )


def get_latest_mapping_confirmation_for_key(
    session: Session, proposal_id: str, mapping_key: str
) -> MappingConfirmation | None:
    return (
        session.query(MappingConfirmation)
        .filter(
            MappingConfirmation.proposal_id == proposal_id,
            MappingConfirmation.mapping_key == mapping_key,
        )
        .order_by(MappingConfirmation.created_at.desc())
        .first()
    )


def create_clarification_audit_event(
    session: Session,
    proposal_id: str,
    event_type: str,
    detail_json: str = "{}",
) -> ClarificationAuditEvent:
    row = ClarificationAuditEvent(
        id=f"clarif_audit_{uuid4().hex[:16]}",
        proposal_id=proposal_id,
        event_type=event_type,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_clarification_audit_events_for_proposal(
    session: Session, proposal_id: str
) -> list[ClarificationAuditEvent]:
    return list(
        session.query(ClarificationAuditEvent)
        .filter(ClarificationAuditEvent.proposal_id == proposal_id)
        .order_by(ClarificationAuditEvent.created_at.asc())
        .all()
    )


# Sprint 31 — Agent Draft Review Bridge to ERPGuard Pipeline


def create_agent_draft_bridge_event(
    session: Session,
    draft_id: str,
    proposal_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> AgentDraftBridgeEvent:
    row = AgentDraftBridgeEvent(
        id=f"bridge_evt_{uuid4().hex[:16]}",
        draft_id=draft_id,
        proposal_id=proposal_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_draft_bridge_events_for_draft(
    session: Session, draft_id: str
) -> list[AgentDraftBridgeEvent]:
    return list(
        session.query(AgentDraftBridgeEvent)
        .filter(AgentDraftBridgeEvent.draft_id == draft_id)
        .order_by(AgentDraftBridgeEvent.created_at.asc())
        .all()
    )


# Sprint 32 — Agent Draft Dry-Run Proof & Approval Handoff


def create_agent_draft_handoff_event(
    session: Session,
    draft_id: str,
    proposal_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> AgentDraftHandoffEvent:
    row = AgentDraftHandoffEvent(
        id=f"handoff_evt_{uuid4().hex[:16]}",
        draft_id=draft_id,
        proposal_id=proposal_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_draft_handoff_events_for_draft(
    session: Session, draft_id: str
) -> list[AgentDraftHandoffEvent]:
    return list(
        session.query(AgentDraftHandoffEvent)
        .filter(AgentDraftHandoffEvent.draft_id == draft_id)
        .order_by(AgentDraftHandoffEvent.created_at.asc())
        .all()
    )


def create_agent_draft_handoff_packet(
    session: Session,
    draft_id: str,
    proposal_id: str,
    packet_json: str,
    status: str = "pending_human_review",
) -> AgentDraftHandoffPacket:
    row = AgentDraftHandoffPacket(
        id=f"handoff_pkt_{uuid4().hex[:16]}",
        draft_id=draft_id,
        proposal_id=proposal_id,
        status=status,
        packet_json=packet_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_latest_agent_draft_handoff_packet(
    session: Session, draft_id: str
) -> AgentDraftHandoffPacket | None:
    return (
        session.query(AgentDraftHandoffPacket)
        .filter(AgentDraftHandoffPacket.draft_id == draft_id)
        .order_by(AgentDraftHandoffPacket.created_at.desc())
        .first()
    )


def get_agent_draft_handoff_packet_by_id(
    session: Session, packet_id: str
) -> AgentDraftHandoffPacket | None:
    return session.get(AgentDraftHandoffPacket, packet_id)


# Sprint 34 — Agent-to-Skill Versioning Handoff


def create_agent_handoff_version_link(
    session: Session,
    *,
    packet_id: str,
    draft_id: str,
    proposal_id: str,
    version_id: str,
    skill_id: str,
) -> "AgentHandoffVersionLink":
    from erpguard.db.models import AgentHandoffVersionLink

    row = AgentHandoffVersionLink(
        id=f"ahvl_{uuid4().hex[:16]}",
        packet_id=packet_id,
        draft_id=draft_id,
        proposal_id=proposal_id,
        version_id=version_id,
        skill_id=skill_id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_agent_handoff_version_link_by_packet(
    session: Session, packet_id: str
) -> "AgentHandoffVersionLink | None":
    from erpguard.db.models import AgentHandoffVersionLink

    return (
        session.query(AgentHandoffVersionLink)
        .filter(AgentHandoffVersionLink.packet_id == packet_id)
        .first()
    )


def create_agent_handoff_version_event(
    session: Session,
    packet_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> "AgentHandoffVersionEvent":
    from erpguard.db.models import AgentHandoffVersionEvent

    row = AgentHandoffVersionEvent(
        id=f"ahve_{uuid4().hex[:16]}",
        packet_id=packet_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_handoff_version_events_for_packet(
    session: Session, packet_id: str
) -> list["AgentHandoffVersionEvent"]:
    from erpguard.db.models import AgentHandoffVersionEvent

    return (
        session.query(AgentHandoffVersionEvent)
        .filter(AgentHandoffVersionEvent.packet_id == packet_id)
        .order_by(AgentHandoffVersionEvent.created_at.asc())
        .all()
    )


# Sprint 35 — Agent Candidate Promotion Readiness & Human Approval Bridge


def create_agent_candidate_approval_packet(
    session: Session,
    *,
    version_id: str,
    skill_id: str,
    packet_json: str = "{}",
) -> "AgentCandidateApprovalPacket":
    from erpguard.db.models import AgentCandidateApprovalPacket

    row = AgentCandidateApprovalPacket(
        id=f"acap_{uuid4().hex[:16]}",
        version_id=version_id,
        skill_id=skill_id,
        packet_json=packet_json,
        status="pending_human_review",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_agent_candidate_approval_packet_by_version(
    session: Session, version_id: str
) -> "AgentCandidateApprovalPacket | None":
    from erpguard.db.models import AgentCandidateApprovalPacket

    return (
        session.query(AgentCandidateApprovalPacket)
        .filter(AgentCandidateApprovalPacket.version_id == version_id)
        .order_by(AgentCandidateApprovalPacket.created_at.desc())
        .first()
    )


def create_agent_candidate_approval_event(
    session: Session,
    version_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> "AgentCandidateApprovalEvent":
    from erpguard.db.models import AgentCandidateApprovalEvent

    row = AgentCandidateApprovalEvent(
        id=f"acae_{uuid4().hex[:16]}",
        version_id=version_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_candidate_approval_events_for_version(
    session: Session, version_id: str
) -> list["AgentCandidateApprovalEvent"]:
    from erpguard.db.models import AgentCandidateApprovalEvent

    return (
        session.query(AgentCandidateApprovalEvent)
        .filter(AgentCandidateApprovalEvent.version_id == version_id)
        .order_by(AgentCandidateApprovalEvent.created_at.asc())
        .all()
    )


# Sprint 36 — Agent Candidate Human Decision & Activation Gate Bridge


def create_agent_candidate_decision(
    session: Session,
    *,
    version_id: str,
    decision: str,
    actor: str,
    rationale: str = "",
    detail_json: str = "{}",
) -> "AgentCandidateDecision":
    from erpguard.db.models import AgentCandidateDecision

    row = AgentCandidateDecision(
        id=f"acd_{uuid4().hex[:16]}",
        version_id=version_id,
        decision=decision,
        actor=actor,
        rationale=rationale,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_candidate_decisions_for_version(
    session: Session, version_id: str
) -> list["AgentCandidateDecision"]:
    from erpguard.db.models import AgentCandidateDecision

    return (
        session.query(AgentCandidateDecision)
        .filter(AgentCandidateDecision.version_id == version_id)
        .order_by(AgentCandidateDecision.created_at.asc())
        .all()
    )


def get_latest_agent_candidate_decision(
    session: Session, version_id: str
) -> "AgentCandidateDecision | None":
    from erpguard.db.models import AgentCandidateDecision

    return (
        session.query(AgentCandidateDecision)
        .filter(AgentCandidateDecision.version_id == version_id)
        .order_by(AgentCandidateDecision.created_at.desc())
        .first()
    )


def create_agent_candidate_decision_event(
    session: Session,
    version_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> "AgentCandidateDecisionEvent":
    from erpguard.db.models import AgentCandidateDecisionEvent

    row = AgentCandidateDecisionEvent(
        id=f"acde_{uuid4().hex[:16]}",
        version_id=version_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_candidate_decision_events_for_version(
    session: Session, version_id: str
) -> list["AgentCandidateDecisionEvent"]:
    from erpguard.db.models import AgentCandidateDecisionEvent

    return (
        session.query(AgentCandidateDecisionEvent)
        .filter(AgentCandidateDecisionEvent.version_id == version_id)
        .order_by(AgentCandidateDecisionEvent.created_at.asc())
        .all()
    )


# Sprint 37 — Explicit Agent Candidate Activation Request


def create_agent_candidate_activation_request(
    session: Session,
    *,
    version_id: str,
    skill_id: str,
    requested_by: str,
    rationale: str = "",
    detail_json: str = "{}",
) -> "AgentCandidateActivationRequest":
    from erpguard.db.models import AgentCandidateActivationRequest

    row = AgentCandidateActivationRequest(
        id=f"acar_{uuid4().hex[:16]}",
        version_id=version_id,
        skill_id=skill_id,
        requested_by=requested_by,
        rationale=rationale,
        request_status="pending_review",
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_agent_candidate_activation_request_by_version(
    session: Session, version_id: str
) -> "AgentCandidateActivationRequest | None":
    from erpguard.db.models import AgentCandidateActivationRequest

    return (
        session.query(AgentCandidateActivationRequest)
        .filter(AgentCandidateActivationRequest.version_id == version_id)
        .order_by(AgentCandidateActivationRequest.created_at.desc())
        .first()
    )


def create_agent_candidate_activation_request_event(
    session: Session,
    version_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> "AgentCandidateActivationRequestEvent":
    from erpguard.db.models import AgentCandidateActivationRequestEvent

    row = AgentCandidateActivationRequestEvent(
        id=f"acare_{uuid4().hex[:16]}",
        version_id=version_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_candidate_activation_request_events_for_version(
    session: Session, version_id: str
) -> list["AgentCandidateActivationRequestEvent"]:
    from erpguard.db.models import AgentCandidateActivationRequestEvent

    return (
        session.query(AgentCandidateActivationRequestEvent)
        .filter(AgentCandidateActivationRequestEvent.version_id == version_id)
        .order_by(AgentCandidateActivationRequestEvent.created_at.asc())
        .all()
    )


# Sprint 38 — Explicit Candidate Activation Without Execution


def create_agent_candidate_activation_event(
    session: Session,
    *,
    version_id: str,
    skill_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> "AgentCandidateActivationEvent":
    from erpguard.db.models import AgentCandidateActivationEvent

    row = AgentCandidateActivationEvent(
        id=f"acav_{uuid4().hex[:16]}",
        version_id=version_id,
        skill_id=skill_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_candidate_activation_events_for_version(
    session: Session, version_id: str
) -> list["AgentCandidateActivationEvent"]:
    from erpguard.db.models import AgentCandidateActivationEvent

    return (
        session.query(AgentCandidateActivationEvent)
        .filter(AgentCandidateActivationEvent.version_id == version_id)
        .order_by(AgentCandidateActivationEvent.created_at.asc())
        .all()
    )


# Sprint 39 — Explicit Active Agent Skill Manual Run Preview


def create_agent_skill_run_preview_event(
    session: Session,
    *,
    version_id: str,
    skill_id: str,
    step: str,
    status: str,
    detail_json: str = "{}",
) -> "AgentSkillRunPreviewEvent":
    from erpguard.db.models import AgentSkillRunPreviewEvent

    row = AgentSkillRunPreviewEvent(
        id=f"asrpe_{uuid4().hex[:16]}",
        version_id=version_id,
        skill_id=skill_id,
        step=step,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_agent_skill_run_preview_events_for_version(
    session: Session, version_id: str
) -> list["AgentSkillRunPreviewEvent"]:
    from erpguard.db.models import AgentSkillRunPreviewEvent

    return (
        session.query(AgentSkillRunPreviewEvent)
        .filter(AgentSkillRunPreviewEvent.version_id == version_id)
        .order_by(AgentSkillRunPreviewEvent.created_at.asc())
        .all()
    )


# Sprint 41 - Conversational Operator Console


def create_operator_console_session(
    session: Session, *, actor: str = "operator"
) -> OperatorConsoleSession:
    from uuid import uuid4

    row = OperatorConsoleSession(id=f"ocses_{uuid4().hex[:16]}", actor=actor)
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_operator_console_session(
    session: Session, session_id: str
) -> OperatorConsoleSession | None:
    return session.get(OperatorConsoleSession, session_id)


def create_operator_console_query(
    session: Session,
    *,
    session_id: str,
    query_text: str,
    detected_intent: str = "unknown",
    intent_confidence: float = 0.0,
    version_id_context: str | None = None,
    response_summary: str = "",
    result_type: str = "",
) -> OperatorConsoleQuery:
    from uuid import uuid4

    row = OperatorConsoleQuery(
        id=f"ocqry_{uuid4().hex[:16]}",
        session_id=session_id,
        query_text=query_text,
        detected_intent=detected_intent,
        intent_confidence=intent_confidence,
        version_id_context=version_id_context,
        response_summary=response_summary,
        result_type=result_type,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_operator_console_queries(
    session: Session, session_id: str
) -> list[OperatorConsoleQuery]:
    return list(
        session.query(OperatorConsoleQuery)
        .filter(OperatorConsoleQuery.session_id == session_id)
        .order_by(OperatorConsoleQuery.created_at.asc())
        .all()
    )


def list_recent_operator_console_queries(
    session: Session, *, limit: int = 50
) -> list[OperatorConsoleQuery]:
    return list(
        session.query(OperatorConsoleQuery)
        .order_by(OperatorConsoleQuery.created_at.desc())
        .limit(limit)
        .all()
    )


def create_operator_action_plan_event(
    session: Session,
    *,
    plan_id: str,
    plan_type: str,
    goal: str,
    version_id_context: str | None,
    step_count: int,
    blocking_count: int,
) -> OperatorActionPlanEvent:
    row = OperatorActionPlanEvent(
        id=plan_id,
        plan_type=plan_type,
        goal=goal,
        version_id_context=version_id_context,
        step_count=step_count,
        blocking_count=blocking_count,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_recent_operator_action_plan_events(
    session: Session, *, limit: int = 50
) -> list[OperatorActionPlanEvent]:
    return list(
        session.query(OperatorActionPlanEvent)
        .order_by(OperatorActionPlanEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def count_operator_action_plan_events(session: Session) -> int:
    return session.query(OperatorActionPlanEvent).count()


def create_action_plan_step_token(
    session: Session,
    *,
    token_id: str,
    plan_id: str,
    step_number: int,
    step_title: str,
    endpoint_hint: str,
    method_hint: str,
    severity: str,
    risk_level: str,
    risk_summary: str,
    expires_at,
) -> ActionPlanStepToken:
    row = ActionPlanStepToken(
        id=token_id,
        plan_id=plan_id,
        step_number=step_number,
        step_title=step_title,
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        severity=severity,
        risk_level=risk_level,
        risk_summary=risk_summary,
        status="pending",
        expires_at=expires_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_action_plan_step_token(
    session: Session, token_id: str
) -> ActionPlanStepToken | None:
    return (
        session.query(ActionPlanStepToken)
        .filter(ActionPlanStepToken.id == token_id)
        .first()
    )


def confirm_action_plan_step_token(
    session: Session, token_id: str, confirmed_at
) -> ActionPlanStepToken | None:
    row = get_action_plan_step_token(session, token_id)
    if row is None:
        return None
    row.status = "confirmed"
    row.confirmed_at = confirmed_at
    session.commit()
    session.refresh(row)
    return row


def expire_action_plan_step_tokens(session: Session, now) -> int:
    rows = (
        session.query(ActionPlanStepToken)
        .filter(ActionPlanStepToken.status == "pending")
        .filter(ActionPlanStepToken.expires_at <= now)
        .all()
    )
    for row in rows:
        row.status = "expired"
    if rows:
        session.commit()
    return len(rows)


def create_action_dispatch_eligibility_event(
    session: Session,
    *,
    event_id: str,
    action_key: str,
    endpoint_hint: str,
    token_id: str | None,
    version_id: str | None,
    eligible: bool,
    blocked_reason: str | None,
    policy_name: str | None,
) -> ActionDispatchEligibilityEvent:
    row = ActionDispatchEligibilityEvent(
        id=event_id,
        action_key=action_key,
        endpoint_hint=endpoint_hint,
        token_id=token_id,
        version_id=version_id,
        eligible=eligible,
        blocked_reason=blocked_reason,
        policy_name=policy_name,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_recent_dispatch_eligibility_events(
    session: Session, *, limit: int = 50
) -> list[ActionDispatchEligibilityEvent]:
    return list(
        session.query(ActionDispatchEligibilityEvent)
        .order_by(ActionDispatchEligibilityEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def count_action_dispatch_eligibility_events(session: Session) -> int:
    return session.query(ActionDispatchEligibilityEvent).count()


def create_action_dispatch_result_record(
    session: Session,
    *,
    dispatch_id: str,
    action_key: str,
    status: str,
    handler_type: str,
    endpoint_hint: str,
    method_hint: str,
    token_id: str | None,
    version_id: str | None,
    parameters_json: str,
    result_payload_json: str,
    result_summary: str,
    blocking_reasons_json: str,
    token_confirmed: bool,
    eligibility_passed: bool,
    dispatch_performed: bool,
    erp_writes_performed: bool,
    browser_control_performed: bool,
    mcp_execution_performed: bool,
    llm_runtime_used: bool,
    system_state_mutated: bool,
    skill_mutated: bool,
    activation_performed: bool,
    scheduling_performed: bool,
    audit_recorded: bool,
) -> ActionDispatchResultRecord:
    row = ActionDispatchResultRecord(
        id=dispatch_id,
        action_key=action_key,
        status=status,
        handler_type=handler_type,
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        token_id=token_id,
        version_id=version_id,
        parameters_json=parameters_json,
        result_payload_json=result_payload_json,
        result_summary=result_summary,
        blocking_reasons_json=blocking_reasons_json,
        token_confirmed=token_confirmed,
        eligibility_passed=eligibility_passed,
        dispatch_performed=dispatch_performed,
        erp_writes_performed=erp_writes_performed,
        browser_control_performed=browser_control_performed,
        mcp_execution_performed=mcp_execution_performed,
        llm_runtime_used=llm_runtime_used,
        system_state_mutated=system_state_mutated,
        skill_mutated=skill_mutated,
        activation_performed=activation_performed,
        scheduling_performed=scheduling_performed,
        audit_recorded=audit_recorded,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_action_dispatch_result_record(
    session: Session, dispatch_id: str
) -> ActionDispatchResultRecord | None:
    return (
        session.query(ActionDispatchResultRecord)
        .filter(ActionDispatchResultRecord.id == dispatch_id)
        .first()
    )


def create_action_dispatch_execution_audit_event(
    session: Session,
    *,
    event_id: str,
    dispatch_id: str,
    action_key: str,
    event_type: str,
    status: str,
    handler_type: str,
    endpoint_hint: str,
    method_hint: str,
    token_id: str | None,
    version_id: str | None,
    detail_json: str,
) -> ActionDispatchExecutionAuditEvent:
    row = ActionDispatchExecutionAuditEvent(
        id=event_id,
        dispatch_id=dispatch_id,
        action_key=action_key,
        event_type=event_type,
        status=status,
        handler_type=handler_type,
        endpoint_hint=endpoint_hint,
        method_hint=method_hint,
        token_id=token_id,
        version_id=version_id,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_recent_action_dispatch_execution_audit_events(
    session: Session, *, limit: int = 50
) -> list[ActionDispatchExecutionAuditEvent]:
    return list(
        session.query(ActionDispatchExecutionAuditEvent)
        .order_by(ActionDispatchExecutionAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


# Sprint 47 — Manual Dry-Run Execution Record


def create_manual_dry_run_evidence(
    session: Session,
    *,
    run_id: str,
    version_id: str,
    skill_id: str,
    actor_json: str,
    mode: str,
    inputs_json: str,
    preview_reference_id: str | None,
    source_plan_id: str | None,
    source_step_number: int | None,
    gate_result_json: str,
    simulated_steps_json: str,
    would_execute_steps_json: str,
    blocked_steps_json: str,
    safety_summary_json: str,
) -> ManualDryRunEvidence:
    row = ManualDryRunEvidence(
        id=f"runev_{uuid4().hex[:16]}",
        run_id=run_id,
        version_id=version_id,
        skill_id=skill_id,
        actor_json=actor_json,
        mode=mode,
        inputs_json=inputs_json,
        preview_reference_id=preview_reference_id,
        source_plan_id=source_plan_id,
        source_step_number=source_step_number,
        gate_result_json=gate_result_json,
        simulated_steps_json=simulated_steps_json,
        would_execute_steps_json=would_execute_steps_json,
        blocked_steps_json=blocked_steps_json,
        safety_summary_json=safety_summary_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_manual_dry_run_evidence_for_run(
    session: Session, run_id: str
) -> ManualDryRunEvidence | None:
    return (
        session.query(ManualDryRunEvidence)
        .filter(ManualDryRunEvidence.run_id == run_id)
        .first()
    )


def create_manual_dry_run_audit_event(
    session: Session,
    *,
    run_id: str,
    version_id: str,
    actor_json: str,
    event_type: str,
    status: str,
    detail_json: str = "{}",
) -> ManualDryRunAuditEvent:
    row = ManualDryRunAuditEvent(
        id=f"mdr_aud_{uuid4().hex[:16]}",
        run_id=run_id,
        version_id=version_id,
        actor_json=actor_json,
        event_type=event_type,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_manual_dry_run_audit_events_for_run(
    session: Session, run_id: str
) -> list[ManualDryRunAuditEvent]:
    return list(
        session.query(ManualDryRunAuditEvent)
        .filter(ManualDryRunAuditEvent.run_id == run_id)
        .order_by(ManualDryRunAuditEvent.created_at.asc())
        .all()
    )


def list_recent_manual_dry_run_audit_events(
    session: Session, *, limit: int = 50
) -> list[ManualDryRunAuditEvent]:
    return list(
        session.query(ManualDryRunAuditEvent)
        .order_by(ManualDryRunAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


# Sprint 48 — Controlled Fake ERP Execution


def create_fake_erp_execution_record(
    session: Session,
    *,
    execution_id: str,
    version_id: str,
    skill_id: str,
    dry_run_id: str,
    actor_json: str,
    execution_target: str,
    inputs_json: str,
    status: str,
    step_count: int,
    steps_executed: int,
    steps_blocked: int,
    result_summary: str,
    safety_summary_json: str,
    evidence_pack_id: str | None = None,
    finished_at=None,
) -> FakeERPExecutionRecord:
    row = FakeERPExecutionRecord(
        id=execution_id,
        version_id=version_id,
        skill_id=skill_id,
        dry_run_id=dry_run_id,
        actor_json=actor_json,
        execution_target=execution_target,
        inputs_json=inputs_json,
        status=status,
        step_count=step_count,
        steps_executed=steps_executed,
        steps_blocked=steps_blocked,
        result_summary=result_summary,
        safety_summary_json=safety_summary_json,
        evidence_pack_id=evidence_pack_id,
        finished_at=finished_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_fake_erp_execution_record(
    session: Session, execution_id: str
) -> FakeERPExecutionRecord | None:
    return session.get(FakeERPExecutionRecord, execution_id)


def update_fake_erp_execution_record(
    session: Session,
    execution_id: str,
    *,
    status: str | None = None,
    step_count: int | None = None,
    steps_executed: int | None = None,
    steps_blocked: int | None = None,
    result_summary: str | None = None,
    safety_summary_json: str | None = None,
    evidence_pack_id: str | None = None,
    finished_at=None,
) -> FakeERPExecutionRecord | None:
    row = session.get(FakeERPExecutionRecord, execution_id)
    if row is None:
        return None
    if status is not None:
        row.status = status
    if step_count is not None:
        row.step_count = step_count
    if steps_executed is not None:
        row.steps_executed = steps_executed
    if steps_blocked is not None:
        row.steps_blocked = steps_blocked
    if result_summary is not None:
        row.result_summary = result_summary
    if safety_summary_json is not None:
        row.safety_summary_json = safety_summary_json
    if evidence_pack_id is not None:
        row.evidence_pack_id = evidence_pack_id
    if finished_at is not None:
        row.finished_at = finished_at
    session.commit()
    session.refresh(row)
    return row


def create_fake_erp_execution_evidence(
    session: Session,
    *,
    execution_id: str,
    version_id: str,
    skill_id: str,
    dry_run_id: str,
    actor_json: str,
    execution_target: str,
    inputs_json: str,
    steps_json: str,
    safety_summary_json: str,
) -> FakeERPExecutionEvidence:
    row = FakeERPExecutionEvidence(
        id=f"fepack_{uuid4().hex[:16]}",
        execution_id=execution_id,
        version_id=version_id,
        skill_id=skill_id,
        dry_run_id=dry_run_id,
        actor_json=actor_json,
        execution_target=execution_target,
        inputs_json=inputs_json,
        steps_json=steps_json,
        safety_summary_json=safety_summary_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_fake_erp_execution_evidence(
    session: Session, execution_id: str
) -> FakeERPExecutionEvidence | None:
    return (
        session.query(FakeERPExecutionEvidence)
        .filter(FakeERPExecutionEvidence.execution_id == execution_id)
        .first()
    )


def create_fake_erp_execution_audit_event(
    session: Session,
    *,
    execution_id: str,
    version_id: str,
    dry_run_id: str,
    actor_json: str,
    event_type: str,
    status: str,
    detail_json: str = "{}",
) -> FakeERPExecutionAuditEvent:
    row = FakeERPExecutionAuditEvent(
        id=f"fea_{uuid4().hex[:16]}",
        execution_id=execution_id,
        version_id=version_id,
        dry_run_id=dry_run_id,
        actor_json=actor_json,
        event_type=event_type,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_recent_fake_erp_execution_audit_events(
    session: Session, *, limit: int = 50
) -> list[FakeERPExecutionAuditEvent]:
    return list(
        session.query(FakeERPExecutionAuditEvent)
        .order_by(FakeERPExecutionAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


# Sprint 49 — Persisted Fake ERP Evidence Pack


def create_fake_erp_execution_evidence_pack(
    session: Session,
    *,
    pack_id: str,
    execution_id: str,
    version_id: str,
    skill_id: str,
    dry_run_id: str,
    actor_json: str,
    inputs_json: str,
    result_snapshot_json: str,
    steps_snapshot_json: str,
    safety_summary_json: str,
    audit_snapshot_json: str,
) -> FakeERPExecutionEvidencePack:
    row = FakeERPExecutionEvidencePack(
        id=pack_id,
        execution_id=execution_id,
        version_id=version_id,
        skill_id=skill_id,
        dry_run_id=dry_run_id,
        actor_json=actor_json,
        inputs_json=inputs_json,
        result_snapshot_json=result_snapshot_json,
        steps_snapshot_json=steps_snapshot_json,
        safety_summary_json=safety_summary_json,
        audit_snapshot_json=audit_snapshot_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_fake_erp_execution_evidence_pack(
    session: Session, pack_id: str
) -> FakeERPExecutionEvidencePack | None:
    return session.get(FakeERPExecutionEvidencePack, pack_id)


def get_latest_fake_erp_execution_evidence_pack_for_execution(
    session: Session, execution_id: str
) -> FakeERPExecutionEvidencePack | None:
    return (
        session.query(FakeERPExecutionEvidencePack)
        .filter(FakeERPExecutionEvidencePack.execution_id == execution_id)
        .order_by(FakeERPExecutionEvidencePack.created_at.desc())
        .first()
    )


# Sprint 50 — Manual Fake ERP Regression Suite


def create_fake_erp_regression_case(
    session: Session,
    *,
    case_id: str,
    version_id: str,
    dry_run_id: str,
    name: str,
    execution_target: str,
    inputs_json: str,
    expected_outcomes_json: str,
) -> FakeERPRegressionCase:
    row = FakeERPRegressionCase(
        id=case_id,
        version_id=version_id,
        dry_run_id=dry_run_id,
        name=name,
        execution_target=execution_target,
        inputs_json=inputs_json,
        expected_outcomes_json=expected_outcomes_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_fake_erp_regression_case(
    session: Session, case_id: str
) -> FakeERPRegressionCase | None:
    return session.get(FakeERPRegressionCase, case_id)


def create_fake_erp_regression_run(
    session: Session,
    *,
    regression_run_id: str,
    case_id: str,
    version_id: str,
    dry_run_id: str,
    actor_json: str,
    inputs_json: str,
    execution_target: str,
    status: str,
    comparison_summary_json: str,
    result_summary: str,
    safety_summary_json: str,
    execution_id: str | None = None,
    evidence_pack_id: str | None = None,
    finished_at=None,
) -> FakeERPRegressionRun:
    row = FakeERPRegressionRun(
        id=regression_run_id,
        case_id=case_id,
        version_id=version_id,
        dry_run_id=dry_run_id,
        execution_id=execution_id,
        evidence_pack_id=evidence_pack_id,
        actor_json=actor_json,
        inputs_json=inputs_json,
        execution_target=execution_target,
        status=status,
        comparison_summary_json=comparison_summary_json,
        result_summary=result_summary,
        safety_summary_json=safety_summary_json,
        finished_at=finished_at,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_fake_erp_regression_run(
    session: Session, regression_run_id: str
) -> FakeERPRegressionRun | None:
    return session.get(FakeERPRegressionRun, regression_run_id)


def update_fake_erp_regression_run(
    session: Session,
    regression_run_id: str,
    *,
    execution_id: str | None = None,
    evidence_pack_id: str | None = None,
    status: str | None = None,
    comparison_summary_json: str | None = None,
    result_summary: str | None = None,
    safety_summary_json: str | None = None,
    finished_at=None,
) -> FakeERPRegressionRun | None:
    row = session.get(FakeERPRegressionRun, regression_run_id)
    if row is None:
        return None
    if execution_id is not None:
        row.execution_id = execution_id
    if evidence_pack_id is not None:
        row.evidence_pack_id = evidence_pack_id
    if status is not None:
        row.status = status
    if comparison_summary_json is not None:
        row.comparison_summary_json = comparison_summary_json
    if result_summary is not None:
        row.result_summary = result_summary
    if safety_summary_json is not None:
        row.safety_summary_json = safety_summary_json
    if finished_at is not None:
        row.finished_at = finished_at
    session.commit()
    session.refresh(row)
    return row


def create_fake_erp_regression_audit_event(
    session: Session,
    *,
    audit_event_id: str,
    regression_run_id: str,
    case_id: str,
    version_id: str,
    execution_id: str | None,
    evidence_pack_id: str | None,
    actor_json: str,
    event_type: str,
    status: str,
    detail_json: str = "{}",
) -> FakeERPRegressionAuditEvent:
    row = FakeERPRegressionAuditEvent(
        id=audit_event_id,
        regression_run_id=regression_run_id,
        case_id=case_id,
        version_id=version_id,
        execution_id=execution_id,
        evidence_pack_id=evidence_pack_id,
        actor_json=actor_json,
        event_type=event_type,
        status=status,
        detail_json=detail_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_recent_fake_erp_regression_audit_events(
    session: Session, *, limit: int = 50
) -> list[FakeERPRegressionAuditEvent]:
    return list(
        session.query(FakeERPRegressionAuditEvent)
        .order_by(FakeERPRegressionAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


# Sprint 55 — Connector Credential Vault Contract


def create_credential_vault_entry(
    session: Session,
    *,
    credential_ref: str,
    setup_session_id: str,
    connector_name: str,
    erp_url_host: str,
    auth_type: str,
    username_redacted: str | None,
    secret_fingerprint: str,
    secret_length: int | None,
    secret_last4: str | None,
    status: str,
    created_by: str,
    blocking_reasons_json: str,
) -> CredentialVaultEntry:
    row = CredentialVaultEntry(
        id=f"credv_{uuid4().hex[:12]}",
        credential_ref=credential_ref,
        setup_session_id=setup_session_id,
        connector_name=connector_name,
        erp_url_host=erp_url_host,
        auth_type=auth_type,
        username_redacted=username_redacted,
        secret_fingerprint=secret_fingerprint,
        secret_length=secret_length,
        secret_last4=secret_last4,
        status=status,
        created_by=created_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_credential_vault_entry_by_ref(
    session: Session, credential_ref: str
) -> CredentialVaultEntry | None:
    return (
        session.query(CredentialVaultEntry)
        .filter(CredentialVaultEntry.credential_ref == credential_ref)
        .first()
    )


def revoke_credential_vault_entry(
    session: Session, credential_ref: str
) -> CredentialVaultEntry | None:
    from datetime import datetime, timezone

    row = get_credential_vault_entry_by_ref(session, credential_ref)
    if row is None:
        return None
    row.status = "revoked"
    row.revoked_at = datetime.now(timezone.utc)
    session.commit()
    session.refresh(row)
    return row


def create_credential_vault_audit_event(
    session: Session,
    *,
    credential_ref: str,
    setup_session_id: str,
    event_type: str,
    auth_type: str,
    status: str,
    username_redacted: str | None,
    secret_fingerprint: str,
    created_by: str,
    details_json: str,
) -> CredentialVaultAuditEvent:
    row = CredentialVaultAuditEvent(
        id=f"credva_{uuid4().hex[:12]}",
        credential_ref=credential_ref,
        setup_session_id=setup_session_id,
        event_type=event_type,
        auth_type=auth_type,
        status=status,
        username_redacted=username_redacted,
        secret_fingerprint=secret_fingerprint,
        created_by=created_by,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_credential_vault_audit_events(
    session: Session, *, limit: int = 50
) -> list[CredentialVaultAuditEvent]:
    return list(
        session.query(CredentialVaultAuditEvent)
        .order_by(CredentialVaultAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_erp_fingerprinting_plan(
    session: Session,
    *,
    fingerprint_plan_id: str,
    setup_session_id: str,
    credential_ref: str,
    connector_name: str,
    erp_url_host: str,
    environment_type: str,
    status: str = "planned",
    adapter_candidates_json: str = "[]",
    planned_checks_json: str = "[]",
    risk_summary_json: str = "{}",
    next_safe_step: str | None = None,
    confidence: float = 0.0,
    created_by: str = "operator_1",
    blocking_reasons_json: str = "[]",
) -> ERPFingerprintingPlan:
    row = ERPFingerprintingPlan(
        id=fingerprint_plan_id,
        fingerprint_plan_id=fingerprint_plan_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        connector_name=connector_name,
        erp_url_host=erp_url_host,
        environment_type=environment_type,
        status=status,
        adapter_candidates_json=adapter_candidates_json,
        planned_checks_json=planned_checks_json,
        risk_summary_json=risk_summary_json,
        next_safe_step=next_safe_step,
        confidence=confidence,
        created_by=created_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_erp_fingerprinting_plan_by_id(
    session: Session, fingerprint_plan_id: str
) -> ERPFingerprintingPlan | None:
    return (
        session.query(ERPFingerprintingPlan)
        .filter(ERPFingerprintingPlan.fingerprint_plan_id == fingerprint_plan_id)
        .first()
    )


def list_erp_fingerprinting_plans(
    session: Session, *, limit: int = 50
) -> list[ERPFingerprintingPlan]:
    return list(
        session.query(ERPFingerprintingPlan)
        .order_by(ERPFingerprintingPlan.created_at.desc())
        .limit(limit)
        .all()
    )


def create_erp_fingerprinting_audit_event(
    session: Session,
    *,
    fingerprint_plan_id: str,
    setup_session_id: str,
    credential_ref: str,
    event_type: str,
    status: str,
    details_json: str = "{}",
) -> ERPFingerprintingAuditEvent:
    row = ERPFingerprintingAuditEvent(
        id=f"fpaudit_{uuid4().hex[:12]}",
        fingerprint_plan_id=fingerprint_plan_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        event_type=event_type,
        status=status,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_erp_fingerprinting_audit_events(
    session: Session, *, limit: int = 50
) -> list[ERPFingerprintingAuditEvent]:
    return list(
        session.query(ERPFingerprintingAuditEvent)
        .order_by(ERPFingerprintingAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_safe_discovery_plan(
    session: Session,
    *,
    discovery_plan_id: str,
    fingerprint_plan_id: str,
    setup_session_id: str,
    credential_ref: str,
    selected_adapter_type: str,
    connector_name: str,
    erp_url_host: str,
    environment_type: str,
    status: str = "planned",
    read_only_surface_json: str = "{}",
    blocked_write_surface_json: str = "[]",
    permission_surface_json: str = "[]",
    planned_discovery_steps_json: str = "[]",
    risk_summary_json: str = "{}",
    next_safe_step: str | None = None,
    created_by: str = "operator_1",
    blocking_reasons_json: str = "[]",
) -> SafeDiscoveryPlan:
    row = SafeDiscoveryPlan(
        id=discovery_plan_id,
        discovery_plan_id=discovery_plan_id,
        fingerprint_plan_id=fingerprint_plan_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        selected_adapter_type=selected_adapter_type,
        connector_name=connector_name,
        erp_url_host=erp_url_host,
        environment_type=environment_type,
        status=status,
        read_only_surface_json=read_only_surface_json,
        blocked_write_surface_json=blocked_write_surface_json,
        permission_surface_json=permission_surface_json,
        planned_discovery_steps_json=planned_discovery_steps_json,
        risk_summary_json=risk_summary_json,
        next_safe_step=next_safe_step,
        created_by=created_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_safe_discovery_plan_by_id(
    session: Session, discovery_plan_id: str
) -> SafeDiscoveryPlan | None:
    return (
        session.query(SafeDiscoveryPlan)
        .filter(SafeDiscoveryPlan.discovery_plan_id == discovery_plan_id)
        .first()
    )


def list_safe_discovery_plans(
    session: Session, *, limit: int = 50
) -> list[SafeDiscoveryPlan]:
    return list(
        session.query(SafeDiscoveryPlan)
        .order_by(SafeDiscoveryPlan.created_at.desc())
        .limit(limit)
        .all()
    )


def create_safe_discovery_audit_event(
    session: Session,
    *,
    discovery_plan_id: str,
    fingerprint_plan_id: str,
    setup_session_id: str,
    credential_ref: str,
    event_type: str,
    status: str,
    created_by: str,
    details_json: str = "{}",
) -> SafeDiscoveryAuditEvent:
    row = SafeDiscoveryAuditEvent(
        id=f"sdaudit_{uuid4().hex[:12]}",
        discovery_plan_id=discovery_plan_id,
        fingerprint_plan_id=fingerprint_plan_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        event_type=event_type,
        status=status,
        created_by=created_by,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_safe_discovery_audit_events(
    session: Session, *, limit: int = 50
) -> list[SafeDiscoveryAuditEvent]:
    return list(
        session.query(SafeDiscoveryAuditEvent)
        .order_by(SafeDiscoveryAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_generated_capability_set(
    session: Session,
    *,
    capability_set_id: str,
    discovery_plan_id: str,
    fingerprint_plan_id: str,
    setup_session_id: str,
    credential_ref: str,
    adapter_id: str,
    adapter_type: str,
    status: str = "generated",
    capabilities_json: str = "[]",
    blocked_capabilities_json: str = "[]",
    source_surface_snapshot_json: str = "{}",
    policy_summary_json: str = "{}",
    created_by: str = "operator_1",
    blocking_reasons_json: str = "[]",
) -> GeneratedCapabilitySet:
    row = GeneratedCapabilitySet(
        id=capability_set_id,
        capability_set_id=capability_set_id,
        discovery_plan_id=discovery_plan_id,
        fingerprint_plan_id=fingerprint_plan_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        status=status,
        capabilities_json=capabilities_json,
        blocked_capabilities_json=blocked_capabilities_json,
        source_surface_snapshot_json=source_surface_snapshot_json,
        policy_summary_json=policy_summary_json,
        created_by=created_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_generated_capability_set_by_id(
    session: Session, capability_set_id: str
) -> GeneratedCapabilitySet | None:
    return (
        session.query(GeneratedCapabilitySet)
        .filter(GeneratedCapabilitySet.capability_set_id == capability_set_id)
        .first()
    )


def list_generated_capability_sets(
    session: Session, *, limit: int = 50
) -> list[GeneratedCapabilitySet]:
    return list(
        session.query(GeneratedCapabilitySet)
        .order_by(GeneratedCapabilitySet.created_at.desc())
        .limit(limit)
        .all()
    )


def create_generated_capability_audit_event(
    session: Session,
    *,
    capability_set_id: str,
    discovery_plan_id: str,
    fingerprint_plan_id: str,
    setup_session_id: str,
    credential_ref: str,
    event_type: str,
    status: str,
    created_by: str,
    details_json: str = "{}",
) -> GeneratedCapabilityAuditEvent:
    row = GeneratedCapabilityAuditEvent(
        id=f"gcaudit_{uuid4().hex[:12]}",
        capability_set_id=capability_set_id,
        discovery_plan_id=discovery_plan_id,
        fingerprint_plan_id=fingerprint_plan_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        event_type=event_type,
        status=status,
        created_by=created_by,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_generated_capability_audit_events(
    session: Session, *, limit: int = 50
) -> list[GeneratedCapabilityAuditEvent]:
    return list(
        session.query(GeneratedCapabilityAuditEvent)
        .order_by(GeneratedCapabilityAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_read_only_activation_request(
    session: Session,
    *,
    activation_request_id: str,
    capability_set_id: str,
    setup_session_id: str,
    credential_ref: str,
    adapter_id: str,
    adapter_type: str,
    mode: str,
    requested_by: str,
    status: str,
    requires_human_approval: bool = True,
    blocking_reasons_json: str = "[]",
) -> ReadOnlyConnectorActivationRequest:
    row = ReadOnlyConnectorActivationRequest(
        id=activation_request_id,
        activation_request_id=activation_request_id,
        capability_set_id=capability_set_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        mode=mode,
        requested_by=requested_by,
        status=status,
        requires_human_approval=requires_human_approval,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_read_only_activation_request_by_id(
    session: Session, activation_request_id: str
) -> ReadOnlyConnectorActivationRequest | None:
    return (
        session.query(ReadOnlyConnectorActivationRequest)
        .filter(ReadOnlyConnectorActivationRequest.activation_request_id == activation_request_id)
        .first()
    )


def update_read_only_activation_request_status(
    session: Session, activation_request_id: str, status: str
) -> ReadOnlyConnectorActivationRequest | None:
    row = get_read_only_activation_request_by_id(session, activation_request_id)
    if row is None:
        return None
    row.status = status
    session.commit()
    session.refresh(row)
    return row


def create_read_only_connector_activation(
    session: Session,
    *,
    activation_id: str,
    activation_request_id: str,
    capability_set_id: str,
    setup_session_id: str,
    credential_ref: str,
    adapter_id: str,
    adapter_type: str,
    mode: str,
    status: str,
    approved_by: str,
    blocking_reasons_json: str = "[]",
) -> ReadOnlyConnectorActivation:
    row = ReadOnlyConnectorActivation(
        id=activation_id,
        activation_id=activation_id,
        activation_request_id=activation_request_id,
        capability_set_id=capability_set_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        mode=mode,
        status=status,
        approved_by=approved_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_read_only_connector_activation_by_id(
    session: Session, activation_id: str
) -> ReadOnlyConnectorActivation | None:
    return (
        session.query(ReadOnlyConnectorActivation)
        .filter(ReadOnlyConnectorActivation.activation_id == activation_id)
        .first()
    )


def list_read_only_connector_activations(
    session: Session, *, limit: int = 50
) -> list[ReadOnlyConnectorActivation]:
    return list(
        session.query(ReadOnlyConnectorActivation)
        .order_by(ReadOnlyConnectorActivation.created_at.desc())
        .limit(limit)
        .all()
    )


def create_read_only_activation_audit_event(
    session: Session,
    *,
    activation_request_id: str,
    activation_id: str,
    capability_set_id: str,
    setup_session_id: str,
    credential_ref: str,
    event_type: str,
    status: str,
    actor: str,
    details_json: str = "{}",
) -> ReadOnlyConnectorActivationAuditEvent:
    row = ReadOnlyConnectorActivationAuditEvent(
        id=f"roaudit_{uuid4().hex[:12]}",
        activation_request_id=activation_request_id,
        activation_id=activation_id,
        capability_set_id=capability_set_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        event_type=event_type,
        status=status,
        actor=actor,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_read_only_activation_audit_events(
    session: Session, *, limit: int = 50
) -> list[ReadOnlyConnectorActivationAuditEvent]:
    return list(
        session.query(ReadOnlyConnectorActivationAuditEvent)
        .order_by(ReadOnlyConnectorActivationAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_odoo_read_only_adapter_session(
    session: Session,
    *,
    adapter_session_id: str,
    activation_id: str,
    capability_set_id: str,
    setup_session_id: str,
    credential_ref: str,
    adapter_id: str,
    adapter_type: str,
    mode: str,
    status: str,
    created_by: str,
    blocking_reasons_json: str = "[]",
) -> OdooReadOnlyAdapterSession:
    row = OdooReadOnlyAdapterSession(
        id=adapter_session_id,
        adapter_session_id=adapter_session_id,
        activation_id=activation_id,
        capability_set_id=capability_set_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        adapter_id=adapter_id,
        adapter_type=adapter_type,
        mode=mode,
        status=status,
        created_by=created_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_odoo_read_only_adapter_session_by_id(
    session: Session, adapter_session_id: str
) -> OdooReadOnlyAdapterSession | None:
    return (
        session.query(OdooReadOnlyAdapterSession)
        .filter(OdooReadOnlyAdapterSession.adapter_session_id == adapter_session_id)
        .first()
    )


def list_odoo_read_only_adapter_sessions(
    session: Session, *, limit: int = 50
) -> list[OdooReadOnlyAdapterSession]:
    return list(
        session.query(OdooReadOnlyAdapterSession)
        .order_by(OdooReadOnlyAdapterSession.created_at.desc())
        .limit(limit)
        .all()
    )


def create_odoo_read_only_adapter_audit_event(
    session: Session,
    *,
    adapter_session_id: str,
    activation_id: str,
    capability_set_id: str,
    setup_session_id: str,
    credential_ref: str,
    event_type: str,
    status: str,
    actor: str,
    details_json: str = "{}",
) -> OdooReadOnlyAdapterAuditEvent:
    row = OdooReadOnlyAdapterAuditEvent(
        id=f"odooaudit_{uuid4().hex[:12]}",
        adapter_session_id=adapter_session_id,
        activation_id=activation_id,
        capability_set_id=capability_set_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        event_type=event_type,
        status=status,
        actor=actor,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_odoo_read_only_adapter_audit_events(
    session: Session, *, limit: int = 50
) -> list[OdooReadOnlyAdapterAuditEvent]:
    return list(
        session.query(OdooReadOnlyAdapterAuditEvent)
        .order_by(OdooReadOnlyAdapterAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_odoo_connection_test(
    session: Session,
    *,
    connection_test_id: str,
    adapter_session_id: str,
    activation_id: str,
    setup_session_id: str,
    credential_ref: str,
    adapter_type: str,
    status: str,
    network_test_allowed: bool,
    external_http_performed: bool,
    login_attempted: bool,
    login_succeeded: bool,
    odoo_rpc_performed: bool,
    odoo_server_version: str | None,
    requested_by: str,
    blocking_reasons_json: str = "[]",
) -> OdooConnectionTest:
    row = OdooConnectionTest(
        id=connection_test_id,
        connection_test_id=connection_test_id,
        adapter_session_id=adapter_session_id,
        activation_id=activation_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        adapter_type=adapter_type,
        status=status,
        network_test_allowed=network_test_allowed,
        external_http_performed=external_http_performed,
        login_attempted=login_attempted,
        login_succeeded=login_succeeded,
        odoo_rpc_performed=odoo_rpc_performed,
        odoo_server_version=odoo_server_version,
        business_data_read=False,
        schema_inspection_performed=False,
        permission_inspection_performed=False,
        odoo_write_performed=False,
        credentials_exposed=False,
        raw_secret_accessed=False,
        requested_by=requested_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_odoo_connection_test_by_id(
    session: Session, connection_test_id: str
) -> OdooConnectionTest | None:
    return (
        session.query(OdooConnectionTest)
        .filter(OdooConnectionTest.connection_test_id == connection_test_id)
        .first()
    )


def list_odoo_connection_tests(
    session: Session, *, limit: int = 50
) -> list[OdooConnectionTest]:
    return list(
        session.query(OdooConnectionTest)
        .order_by(OdooConnectionTest.created_at.desc())
        .limit(limit)
        .all()
    )


def create_odoo_connection_test_audit_event(
    session: Session,
    *,
    connection_test_id: str,
    adapter_session_id: str,
    activation_id: str,
    setup_session_id: str,
    credential_ref: str,
    event_type: str,
    status: str,
    actor: str,
    details_json: str = "{}",
) -> OdooConnectionTestAuditEvent:
    row = OdooConnectionTestAuditEvent(
        id=f"odooctaudit_{uuid4().hex[:12]}",
        connection_test_id=connection_test_id,
        adapter_session_id=adapter_session_id,
        activation_id=activation_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        event_type=event_type,
        status=status,
        actor=actor,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_odoo_connection_test_audit_events(
    session: Session, *, limit: int = 50
) -> list[OdooConnectionTestAuditEvent]:
    return list(
        session.query(OdooConnectionTestAuditEvent)
        .order_by(OdooConnectionTestAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_odoo_read_mapping(
    session: Session,
    *,
    read_mapping_id: str,
    connection_test_id: str,
    adapter_session_id: str,
    activation_id: str,
    setup_session_id: str,
    credential_ref: str,
    object_type: str,
    status: str,
    allow_business_read: bool,
    business_data_read: bool,
    canonical_object_json: str,
    source_snapshot_redacted_json: str,
    field_allowlist_used_json: str,
    redacted_fields_json: str,
    external_http_performed: bool,
    odoo_rpc_performed: bool,
    odoo_read_performed: bool,
    requested_by: str,
    blocking_reasons_json: str = "[]",
) -> OdooReadMapping:
    row = OdooReadMapping(
        id=read_mapping_id,
        read_mapping_id=read_mapping_id,
        connection_test_id=connection_test_id,
        adapter_session_id=adapter_session_id,
        activation_id=activation_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        object_type=object_type,
        status=status,
        allow_business_read=allow_business_read,
        business_data_read=business_data_read,
        canonical_object_json=canonical_object_json,
        source_snapshot_redacted_json=source_snapshot_redacted_json,
        field_allowlist_used_json=field_allowlist_used_json,
        redacted_fields_json=redacted_fields_json,
        external_http_performed=external_http_performed,
        odoo_rpc_performed=odoo_rpc_performed,
        odoo_read_performed=odoo_read_performed,
        odoo_write_performed=False,
        schema_inspection_performed=False,
        permission_inspection_performed=False,
        credentials_exposed=False,
        raw_secret_accessed=False,
        requested_by=requested_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_odoo_read_mapping_by_id(
    session: Session, read_mapping_id: str
) -> OdooReadMapping | None:
    return (
        session.query(OdooReadMapping)
        .filter(OdooReadMapping.read_mapping_id == read_mapping_id)
        .first()
    )


def list_odoo_read_mappings(
    session: Session, *, limit: int = 50
) -> list[OdooReadMapping]:
    return list(
        session.query(OdooReadMapping)
        .order_by(OdooReadMapping.created_at.desc())
        .limit(limit)
        .all()
    )


def create_odoo_read_mapping_audit_event(
    session: Session,
    *,
    read_mapping_id: str,
    connection_test_id: str,
    adapter_session_id: str,
    activation_id: str,
    setup_session_id: str,
    credential_ref: str,
    object_type: str,
    event_type: str,
    status: str,
    actor: str,
    details_json: str = "{}",
) -> OdooReadMappingAuditEvent:
    row = OdooReadMappingAuditEvent(
        id=f"odoomapaudit_{uuid4().hex[:12]}",
        read_mapping_id=read_mapping_id,
        connection_test_id=connection_test_id,
        adapter_session_id=adapter_session_id,
        activation_id=activation_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        object_type=object_type,
        event_type=event_type,
        status=status,
        actor=actor,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_odoo_read_mapping_audit_events(
    session: Session, *, limit: int = 50
) -> list[OdooReadMappingAuditEvent]:
    return list(
        session.query(OdooReadMappingAuditEvent)
        .order_by(OdooReadMappingAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )


def create_odoo_read_evidence_pack(
    session: Session,
    *,
    evidence_pack_id: str,
    read_mapping_id: str,
    connection_test_id: str,
    adapter_session_id: str,
    activation_id: str,
    setup_session_id: str,
    credential_ref: str,
    object_type: str,
    status: str,
    canonical_object_snapshot_json: str,
    source_snapshot_redacted_json: str,
    field_allowlist_used_json: str,
    redacted_fields_json: str,
    safety_summary_json: str,
    chain_summary_json: str,
    created_by: str,
    blocking_reasons_json: str = "[]",
) -> OdooReadEvidencePack:
    row = OdooReadEvidencePack(
        id=evidence_pack_id,
        evidence_pack_id=evidence_pack_id,
        read_mapping_id=read_mapping_id,
        connection_test_id=connection_test_id,
        adapter_session_id=adapter_session_id,
        activation_id=activation_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        object_type=object_type,
        status=status,
        canonical_object_snapshot_json=canonical_object_snapshot_json,
        source_snapshot_redacted_json=source_snapshot_redacted_json,
        field_allowlist_used_json=field_allowlist_used_json,
        redacted_fields_json=redacted_fields_json,
        safety_summary_json=safety_summary_json,
        chain_summary_json=chain_summary_json,
        created_by=created_by,
        blocking_reasons_json=blocking_reasons_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def get_odoo_read_evidence_pack_by_id(
    session: Session, evidence_pack_id: str
) -> OdooReadEvidencePack | None:
    return (
        session.query(OdooReadEvidencePack)
        .filter(OdooReadEvidencePack.evidence_pack_id == evidence_pack_id)
        .first()
    )


def list_odoo_read_evidence_packs(
    session: Session, *, limit: int = 50
) -> list[OdooReadEvidencePack]:
    return list(
        session.query(OdooReadEvidencePack)
        .order_by(OdooReadEvidencePack.created_at.desc())
        .limit(limit)
        .all()
    )


def create_odoo_read_evidence_audit_event(
    session: Session,
    *,
    evidence_pack_id: str,
    read_mapping_id: str,
    connection_test_id: str,
    adapter_session_id: str,
    activation_id: str,
    setup_session_id: str,
    credential_ref: str,
    object_type: str,
    event_type: str,
    status: str,
    actor: str,
    details_json: str = "{}",
) -> OdooReadEvidenceAuditEvent:
    row = OdooReadEvidenceAuditEvent(
        id=f"odooevaudit_{uuid4().hex[:12]}",
        evidence_pack_id=evidence_pack_id,
        read_mapping_id=read_mapping_id,
        connection_test_id=connection_test_id,
        adapter_session_id=adapter_session_id,
        activation_id=activation_id,
        setup_session_id=setup_session_id,
        credential_ref=credential_ref,
        object_type=object_type,
        event_type=event_type,
        status=status,
        actor=actor,
        details_json=details_json,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def list_odoo_read_evidence_audit_events(
    session: Session, *, limit: int = 50
) -> list[OdooReadEvidenceAuditEvent]:
    return list(
        session.query(OdooReadEvidenceAuditEvent)
        .order_by(OdooReadEvidenceAuditEvent.created_at.desc())
        .limit(limit)
        .all()
    )
