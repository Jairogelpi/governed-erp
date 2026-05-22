from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.record_to_skill import (
    AuditResponse,
    AuditStepEntry,
    CaptureEventRequest,
    CaptureEventResponse,
    CompileUISkillResponse,
    CreateSessionRequest,
    CreateSessionResponse,
    FailureEntryResponse,
    FailuresResponse,
    FinishSessionResponse,
    GenerateDraftRequest,
    GenerateDraftResponse,
    ReplayRequest,
    ReplayResponse,
    ReplayStepResponse,
    ReportResponse,
    RobustReportResponse,
    VerificationEntryResponse,
    VerificationResponse,
    VerifiedReplayResponse,
    VerifiedStepResponse,
)
from erpguard.product.ui_recording_session import UIRecordingSessionService
from erpguard.product.ui_event_capture import UIEventCaptureService
from erpguard.product.ui_recording_normalizer import UIRecordingNormalizerService
from erpguard.product.ui_skill_draft_builder import UISkillDraftBuilder
from erpguard.product.ui_skill_compiler import UISkillCompilerService
from erpguard.product.ui_replay_runtime import UIReplayRuntime
from erpguard.product.ui_replay_audit import UIReplayAuditService
from erpguard.product.ui_replay_report import UIReplayReportService
from erpguard.product.ui_verified_replay_runtime import UIVerifiedReplayRuntime
from erpguard.product.ui_robust_replay_report import UIRobustReplayReportService


router = APIRouter(prefix="/v1/record-to-skill", tags=["record-to-skill"])

_sessions = UIRecordingSessionService()
_events = UIEventCaptureService()
_normalizer = UIRecordingNormalizerService()
_draft_builder = UISkillDraftBuilder()
_compiler = UISkillCompilerService()
_replay = UIReplayRuntime()
_audit = UIReplayAuditService()
_report = UIReplayReportService()
_verified_replay = UIVerifiedReplayRuntime()
_robust_report = UIRobustReplayReportService()


@router.post("/sessions", response_model=CreateSessionResponse)
def create_session(request: CreateSessionRequest):
    result = _sessions.create_session(
        name=request.name,
        description=request.description,
        target_base_url=request.target_base_url,
    )
    return CreateSessionResponse(
        session_id=result.session_id,
        name=result.name,
        description=result.description,
        target_base_url=result.target_base_url,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.get("/sessions/{session_id}", response_model=CreateSessionResponse)
def get_session(session_id: str):
    result = _sessions.get_session(session_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "session_not_found", "session_id": session_id}})
    return CreateSessionResponse(
        session_id=result.session_id,
        name=result.name,
        description=result.description,
        target_base_url=result.target_base_url,
        status=result.status,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post("/sessions/{session_id}/events", response_model=CaptureEventResponse)
def capture_event(session_id: str, request: CaptureEventRequest):
    session = _sessions.get_session(session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"error": {"code": "session_not_found", "session_id": session_id}})
    result = _events.capture_event(
        session_id=session_id,
        event_type=request.event_type,
        url=request.url,
        selector=request.selector,
        element_text=request.element_text,
        element_label=request.element_label,
        input_value=request.input_value,
        metadata=request.metadata,
    )
    return CaptureEventResponse(
        event_id=result.event_id,
        session_id=result.session_id,
        event_index=result.event_index,
        event_type=result.event_type,
        url=result.url,
        selector=result.selector,
        element_text=result.element_text,
        element_label=result.element_label,
        input_value=result.input_value,
        metadata=result.metadata,
        created_at=result.created_at,
    )


@router.post("/sessions/{session_id}/finish", response_model=FinishSessionResponse)
def finish_session(session_id: str):
    result = _sessions.finish_session(session_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "session_not_found", "session_id": session_id}})
    return FinishSessionResponse(session_id=result.session_id, status=result.status)


@router.post("/sessions/{session_id}/generate-draft", response_model=GenerateDraftResponse)
def generate_draft(session_id: str, request: GenerateDraftRequest):
    session = _sessions.get_session(session_id)
    if session is None:
        return JSONResponse(status_code=404, content={"error": {"code": "session_not_found", "session_id": session_id}})
    if session.status != "finished":
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "session_not_finished", "status": session.status}},
        )

    raw_events = _events.list_events(session_id)
    recording = _normalizer.normalize(session_id, raw_events)

    if recording.diagnostics:
        return JSONResponse(
            status_code=400,
            content={"error": {"code": "normalization_failed", "diagnostics": recording.diagnostics}},
        )

    draft = _draft_builder.build_draft(recording, name=request.name, description=request.description)
    return GenerateDraftResponse(
        draft_id=draft.draft_id,
        session_id=draft.session_id,
        name=draft.name,
        description=draft.description,
        steps=draft.steps,
        selector_map=draft.selector_map,
        guard_names=draft.guard_names,
        status=draft.status,
        event_count=len(raw_events),
        normalized_event_count=recording.event_count,
    )


@router.post("/drafts/{draft_id}/compile-ui-skill", response_model=CompileUISkillResponse)
def compile_ui_skill(draft_id: str):
    try:
        result = _compiler.compile(draft_id)
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": {"code": "draft_not_found", "detail": str(exc)}})
    return CompileUISkillResponse(
        compiled_skill_id=result.compiled_skill_id,
        draft_id=result.draft_id,
        session_id=result.session_id,
        name=result.name,
        runtime_type=result.runtime_type,
        steps=result.steps,
        guard_names=result.guard_names,
        llm_required=result.llm_required,
        status=result.status,
    )


@router.post("/compiled-skills/{compiled_skill_id}/replay", response_model=ReplayResponse)
def replay_skill(compiled_skill_id: str, request: ReplayRequest):
    try:
        result = _replay.replay(compiled_skill_id, request.target_base_url)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "replay_error", "detail": str(exc)}})
    return ReplayResponse(
        replay_id=result.replay_id,
        compiled_skill_id=result.compiled_skill_id,
        status=result.status,
        step_count=result.step_count,
        steps_passed=result.steps_passed,
        steps_failed=result.steps_failed,
        step_results=[
            ReplayStepResponse(
                step_index=s.step_index,
                step_id=s.step_id,
                step_type=s.step_type,
                status=s.status,
                before_state=s.before_state,
                after_state=s.after_state,
                evidence=s.evidence,
                error=s.error,
            )
            for s in result.step_results
        ],
        finished_at=result.finished_at,
    )


@router.get("/replays/{replay_id}/audit", response_model=AuditResponse)
def get_replay_audit(replay_id: str):
    result = _audit.get_audit(replay_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "replay_not_found", "replay_id": replay_id}})
    return AuditResponse(
        replay_id=result.replay_id,
        compiled_skill_id=result.compiled_skill_id,
        target_base_url=result.target_base_url,
        replay_status=result.replay_status,
        step_count=result.step_count,
        steps_passed=result.steps_passed,
        steps_failed=result.steps_failed,
        entries=[
            AuditStepEntry(
                audit_id=e.audit_id,
                replay_run_id=e.replay_run_id,
                step_index=e.step_index,
                step_id=e.step_id,
                step_type=e.step_type,
                status=e.status,
                before_state=e.before_state,
                after_state=e.after_state,
                evidence=e.evidence,
                error_text=e.error_text,
                created_at=e.created_at,
            )
            for e in result.entries
        ],
    )


@router.get("/replays/{replay_id}/report", response_model=ReportResponse)
def get_replay_report(replay_id: str):
    result = _report.get_report(replay_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "replay_not_found", "replay_id": replay_id}})
    return ReportResponse(
        replay_id=result.replay_id,
        compiled_skill_id=result.compiled_skill_id,
        target_base_url=result.target_base_url,
        replay_status=result.replay_status,
        step_count=result.step_count,
        steps_passed=result.steps_passed,
        steps_failed=result.steps_failed,
        success_rate_pct=result.success_rate_pct,
        llm_used_at_replay=result.llm_used_at_replay,
        deterministic=result.deterministic,
        audit_evidence_count=result.audit_evidence_count,
        findings=result.findings,
        summary=result.summary,
    )


# Sprint 22 — Verified replay, verification, failures, robust report

@router.post("/compiled-skills/{compiled_skill_id}/verified-replay", response_model=VerifiedReplayResponse)
def verified_replay_skill(compiled_skill_id: str, request: ReplayRequest):
    try:
        result = _verified_replay.replay(compiled_skill_id, request.target_base_url)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "replay_error", "detail": str(exc)}})
    return VerifiedReplayResponse(
        replay_id=result.replay_id,
        compiled_skill_id=result.compiled_skill_id,
        status=result.status,
        step_count=result.step_count,
        steps_passed=result.steps_passed,
        steps_failed=result.steps_failed,
        steps_verification_failed=result.steps_verification_failed,
        step_results=[
            VerifiedStepResponse(
                step_index=s.step_index, step_id=s.step_id, step_type=s.step_type,
                status=s.status, verification_status=s.verification_status,
                before_state=s.before_state, after_state=s.after_state,
                evidence=s.evidence, checks=s.checks,
                failure_type=s.failure_type,
                recovery_suggestion=s.recovery_suggestion,
                error=s.error,
            )
            for s in result.step_results
        ],
        finished_at=result.finished_at,
    )


@router.get("/replays/{replay_id}/verification", response_model=VerificationResponse)
def get_replay_verification(replay_id: str):
    result = _robust_report.get_verifications(replay_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "replay_not_found", "replay_id": replay_id}})
    return VerificationResponse(
        replay_id=replay_id,
        verifications=[
            VerificationEntryResponse(
                step_index=v.step_index, step_id=v.step_id,
                page_state_ok=v.page_state_ok,
                record_identity_ok=v.record_identity_ok,
                selector_ambiguity_ok=v.selector_ambiguity_ok,
                modal_error_ok=v.modal_error_ok,
                post_state_ok=v.post_state_ok,
                overall_status=v.overall_status,
                checks=v.checks,
            )
            for v in result
        ],
    )


@router.get("/replays/{replay_id}/failures", response_model=FailuresResponse)
def get_replay_failures(replay_id: str):
    result = _robust_report.get_failures(replay_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "replay_not_found", "replay_id": replay_id}})
    return FailuresResponse(
        replay_id=replay_id,
        failure_count=len(result),
        failures=[
            FailureEntryResponse(
                step_index=f.step_index, step_id=f.step_id,
                failure_type=f.failure_type, failure_detail=f.failure_detail,
                recovery_suggestion=f.recovery_suggestion, severity=f.severity,
            )
            for f in result
        ],
    )


@router.get("/replays/{replay_id}/robust-report", response_model=RobustReportResponse)
def get_robust_report(replay_id: str):
    result = _robust_report.get_report(replay_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "replay_not_found", "replay_id": replay_id}})
    return RobustReportResponse(
        replay_id=result.replay_id,
        compiled_skill_id=result.compiled_skill_id,
        target_base_url=result.target_base_url,
        replay_status=result.replay_status,
        step_count=result.step_count,
        steps_passed=result.steps_passed,
        steps_failed=result.steps_failed,
        success_rate_pct=result.success_rate_pct,
        llm_used_at_replay=result.llm_used_at_replay,
        deterministic=result.deterministic,
        verification_count=result.verification_count,
        failure_count=result.failure_count,
        verifications=[
            VerificationEntryResponse(
                step_index=v.step_index, step_id=v.step_id,
                page_state_ok=v.page_state_ok, record_identity_ok=v.record_identity_ok,
                selector_ambiguity_ok=v.selector_ambiguity_ok, modal_error_ok=v.modal_error_ok,
                post_state_ok=v.post_state_ok, overall_status=v.overall_status, checks=v.checks,
            )
            for v in result.verifications
        ],
        failures=[
            FailureEntryResponse(
                step_index=f.step_index, step_id=f.step_id,
                failure_type=f.failure_type, failure_detail=f.failure_detail,
                recovery_suggestion=f.recovery_suggestion, severity=f.severity,
            )
            for f in result.failures
        ],
        summary=result.summary,
        recovery_actions_required=result.recovery_actions_required,
    )
