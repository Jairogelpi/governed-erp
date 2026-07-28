from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.agent_skill_run_preview import (
    ExecutionGateCheckSchema,
    ExecutionGateResponse,
    PreviewAuditEventSchema,
    RunPlanResponse,
    RunPlanStepSchema,
    RunPreviewAuditResponse,
    RunPreviewCheckSchema,
    RunPreviewEligibilityResponse,
    RunPreviewResponse,
)
from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.agent_skill_execution_gate import evaluate_execution_gate
from erpguard.product.agent_skill_run_plan_builder import build_run_plan
from erpguard.product.agent_skill_run_preview import get_run_preview
from erpguard.product.agent_skill_run_preview_audit import get_run_preview_audit
from erpguard.product.agent_skill_run_preview_validator import validate_run_preview_eligibility

router = APIRouter(
    prefix="/v1/agent-builder/advisory",
    tags=["agent-skill-run-preview"],
)


def _get_version_or_404(version_id: str, db):
    row = get_ui_skill_version_record(db, version_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"Version '{version_id}' not found.",
        )
    return row


@router.get(
    "/candidates/{version_id}/run-preview/eligibility",
    response_model=RunPreviewEligibilityResponse,
)
def get_run_preview_eligibility(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = validate_run_preview_eligibility(version_id, db)
        return RunPreviewEligibilityResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            eligible=r.eligible,
            checks=[
                RunPreviewCheckSchema(check=c.check, passed=c.passed, detail=c.detail)
                for c in r.checks
            ],
            blocking_reasons=r.blocking_reasons,
            will_execute=r.will_execute,
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()


@router.post(
    "/candidates/{version_id}/run-preview/plan",
    response_model=RunPlanResponse,
)
def post_run_plan(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = build_run_plan(version_id, db)
        return RunPlanResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            plan_ready=r.plan_ready,
            step_count=r.step_count,
            steps=[
                RunPlanStepSchema(
                    step_index=s.step_index,
                    step_id=s.step_id,
                    step_type=s.step_type,
                    description=s.description,
                    guard_check=s.guard_check,
                    will_execute=s.will_execute,
                    estimated_impact=s.estimated_impact,
                )
                for s in r.steps
            ],
            guard_names=r.guard_names,
            runtime_type=r.runtime_type,
            plan_is_dry_run=r.plan_is_dry_run,
            will_execute=r.will_execute,
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/run-preview/execution-gate",
    response_model=ExecutionGateResponse,
)
def get_execution_gate(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = evaluate_execution_gate(version_id, db)
        return ExecutionGateResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            gate_passed=r.gate_passed,
            execution_ready=r.execution_ready,
            checks=[
                ExecutionGateCheckSchema(check=c.check, passed=c.passed, detail=c.detail)
                for c in r.checks
            ],
            blocking_reasons=r.blocking_reasons,
            will_execute=r.will_execute,
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.post(
    "/candidates/{version_id}/run-preview",
    response_model=RunPreviewResponse,
)
def post_run_preview(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_run_preview(version_id, db)
        return RunPreviewResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            preview_ready=r.preview_ready,
            eligible=r.eligible,
            plan_ready=r.plan_ready,
            gate_passed=r.gate_passed,
            execution_ready=r.execution_ready,
            step_count=r.step_count,
            runtime_type=r.runtime_type,
            guard_names=r.guard_names,
            will_execute=r.will_execute,
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
            blocking_reason=r.blocking_reason,
        )
    finally:
        db.close()


@router.get(
    "/candidates/{version_id}/run-preview/audit",
    response_model=RunPreviewAuditResponse,
)
def get_preview_audit(version_id: str):
    init_db()
    db = SessionLocal()
    try:
        _get_version_or_404(version_id, db)
        r = get_run_preview_audit(version_id, db)
        return RunPreviewAuditResponse(
            version_id=r.version_id,
            skill_id=r.skill_id,
            event_count=r.event_count,
            events=[
                PreviewAuditEventSchema(
                    event_id=e.event_id,
                    version_id=e.version_id,
                    step=e.step,
                    status=e.status,
                    detail=e.detail,
                    created_at=e.created_at,
                )
                for e in r.events
            ],
            will_execute=r.will_execute,
            can_execute=r.can_execute,
            is_advisory_only=r.is_advisory_only,
        )
    finally:
        db.close()
