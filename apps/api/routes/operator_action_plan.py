from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from apps.api.schemas.operator_action_plan import (
    ActionPlanAuditEntrySchema,
    ActionPlanAuditResponse,
    ActionPlanRequest,
    ActionPlanResponse,
    ActionPlanStepSchema,
    SupportedPlanTypeSchema,
    SupportedPlanTypesResponse,
)
from apps.api.schemas.operator_step_token import (
    StepConfirmRequest,
    StepConfirmResponse,
    StepPreviewRequest,
    StepPreviewResponse,
    TokenStatusResponse,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.db.repositories import count_operator_action_plan_events
from erpguard.product.operator_action_plan_audit import get_recent_plan_audit, persist_plan_event
from erpguard.product.operator_action_plan_builder import build_action_plan
from erpguard.product.operator_action_plan_intent import classify_plan_intent, list_supported_plan_types
from erpguard.product.operator_action_plan_prerequisites import inspect_prerequisites
from erpguard.product.operator_step_confirmation import confirm_token, get_token_status
from erpguard.product.operator_step_preview import preview_step

router = APIRouter(
    prefix="/v1/operator-console",
    tags=["operator-action-plan"],
)


@router.post("/action-plan", response_model=ActionPlanResponse)
def create_action_plan(body: ActionPlanRequest):
    init_db()
    db = SessionLocal()
    try:
        intent = classify_plan_intent(body.goal)
        pre = inspect_prerequisites(body.version_id, db)
        plan = build_action_plan(intent, body.goal, pre, body.version_id)
        persist_plan_event(plan, db)
        return ActionPlanResponse(
            plan_id=plan.plan_id,
            plan_type=plan.plan_type,
            goal=plan.goal,
            version_id=plan.version_id,
            steps=[
                ActionPlanStepSchema(
                    step_number=s.step_number,
                    title=s.title,
                    description=s.description,
                    endpoint_hint=s.endpoint_hint,
                    method_hint=s.method_hint,
                    severity=s.severity,
                    prereqs_met=s.prereqs_met,
                    blocker_reason=s.blocker_reason,
                    requires_operator_click=s.requires_operator_click,
                    executable=s.executable,
                )
                for s in plan.steps
            ],
            total_steps=plan.total_steps,
            blocking_count=plan.blocking_count,
            advisory_summary=plan.advisory_summary,
        )
    finally:
        db.close()


@router.get("/action-plan/audit", response_model=ActionPlanAuditResponse)
def audit_action_plans(limit: int = Query(default=50, ge=1, le=200)):
    init_db()
    db = SessionLocal()
    try:
        result = get_recent_plan_audit(db, limit=limit)
        return ActionPlanAuditResponse(
            entries=[
                ActionPlanAuditEntrySchema(
                    plan_id=e.plan_id,
                    plan_type=e.plan_type,
                    goal=e.goal,
                    version_id_context=e.version_id_context,
                    step_count=e.step_count,
                    blocking_count=e.blocking_count,
                    created_at=e.created_at,
                )
                for e in result.entries
            ],
            event_count=count_operator_action_plan_events(db),
        )
    finally:
        db.close()


@router.get("/action-plan/plan-types", response_model=SupportedPlanTypesResponse)
def get_supported_plan_types():
    types = list_supported_plan_types()
    return SupportedPlanTypesResponse(
        plan_types=[SupportedPlanTypeSchema(**t) for t in types],
        total=len(types),
    )


# Sprint 43 — step preview & confirmation token endpoints

@router.post("/action-plan/step-preview", response_model=StepPreviewResponse)
def create_step_preview(body: StepPreviewRequest):
    init_db()
    db = SessionLocal()
    try:
        result = preview_step(
            plan_id=body.plan_id,
            step_number=body.step_number,
            step_title=body.step_title,
            endpoint_hint=body.endpoint_hint,
            method_hint=body.method_hint,
            severity=body.severity,
            session=db,
        )
        return StepPreviewResponse(
            token_id=result.token_id,
            plan_id=result.plan_id,
            step_number=result.step_number,
            step_title=result.step_title,
            endpoint_hint=result.endpoint_hint,
            method_hint=result.method_hint,
            severity=result.severity,
            risk_level=result.risk_level,
            risk_summary=result.risk_summary,
            status=result.status,
            expires_at=result.expires_at,
            ttl_seconds=result.ttl_seconds,
        )
    finally:
        db.close()


@router.get("/action-plan/step-preview/{token_id}", response_model=TokenStatusResponse)
def get_step_token_status(token_id: str):
    init_db()
    db = SessionLocal()
    try:
        result = get_token_status(token_id, db)
        if result is None:
            raise HTTPException(status_code=404, detail="Token not found.")
        return TokenStatusResponse(
            token_id=result.token_id,
            plan_id=result.plan_id,
            step_number=result.step_number,
            step_title=result.step_title,
            risk_level=result.risk_level,
            status=result.status,
            expires_at=result.expires_at,
            confirmed_at=result.confirmed_at,
        )
    finally:
        db.close()


@router.post("/action-plan/step-confirm", response_model=StepConfirmResponse)
def confirm_step_token(body: StepConfirmRequest):
    init_db()
    db = SessionLocal()
    try:
        result = confirm_token(body.token_id, db)
        return StepConfirmResponse(
            token_id=result.token_id,
            plan_id=result.plan_id,
            step_number=result.step_number,
            step_title=result.step_title,
            status=result.status,
            confirmed_at=result.confirmed_at,
            message=result.message,
        )
    finally:
        db.close()
