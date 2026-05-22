from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from apps.api.schemas.skill_versioning import (
    ActivationGateResponse,
    CompareVersionsRequest,
    CreateVersionRequest,
    LifecycleAuditResponse,
    LifecycleEventEntryResponse,
    LifecycleTransitionRequest,
    LifecycleTransitionResponse,
    PromotionReadinessResponse,
    RollbackExecuteRequest,
    RollbackPlanResponse,
    RollbackResultResponse,
    StepDiffResponse,
    VersionComparisonResponse,
    VersionDetailResponse,
)
from erpguard.product.skill_versioning import UISkillVersioningService
from erpguard.product.skill_lifecycle import UISkillLifecycleService
from erpguard.product.skill_promotion_readiness import UISkillPromotionReadinessService
from erpguard.product.skill_activation_gate import UISkillActivationGateService
from erpguard.product.skill_version_comparator import UISkillVersionComparator
from erpguard.product.skill_rollback_planner import UISkillRollbackPlanner
from erpguard.product.skill_rollback_service import UISkillRollbackService
from erpguard.product.skill_lifecycle_audit import UISkillLifecycleAuditService


router = APIRouter(prefix="/v1/skills", tags=["skill-versioning"])

_versioning = UISkillVersioningService()
_lifecycle = UISkillLifecycleService()
_readiness = UISkillPromotionReadinessService()
_gate = UISkillActivationGateService()
_comparator = UISkillVersionComparator()
_planner = UISkillRollbackPlanner()
_rollback = UISkillRollbackService()
_audit = UISkillLifecycleAuditService()


def _to_version_response(v) -> VersionDetailResponse:
    return VersionDetailResponse(
        version_id=v.version_id,
        skill_id=v.skill_id,
        compiled_skill_id=v.compiled_skill_id,
        version_number=v.version_number,
        name=v.name,
        status=v.status,
        steps=v.steps,
        guard_names=v.guard_names,
        replay_run_id=v.replay_run_id,
        promotion_readiness=v.promotion_readiness,
        llm_required=v.llm_required,
        runtime_type=v.runtime_type,
        is_active=v.is_active,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


@router.post("/versioning/from-ui-compiled-skill/{compiled_skill_id}", response_model=VersionDetailResponse)
def create_version_from_compiled_skill(compiled_skill_id: str, request: CreateVersionRequest):
    try:
        result = _versioning.create_from_compiled_skill(
            compiled_skill_id,
            skill_id=request.skill_id,
            replay_run_id=request.replay_run_id,
        )
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "detail": str(exc)}})
    return _to_version_response(result)


@router.get("/{skill_id}/versions", response_model=list[VersionDetailResponse])
def list_skill_versions(skill_id: str):
    return [_to_version_response(v) for v in _versioning.list_versions(skill_id)]


@router.get("/versions/{version_id}", response_model=VersionDetailResponse)
def get_skill_version(version_id: str):
    result = _versioning.get_version(version_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "version_not_found", "version_id": version_id}})
    return _to_version_response(result)


@router.post("/versions/{version_id}/promotion-readiness", response_model=PromotionReadinessResponse)
def compute_promotion_readiness(version_id: str):
    try:
        result = _readiness.compute(version_id)
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "detail": str(exc)}})
    return PromotionReadinessResponse(
        version_id=result.version_id,
        ready=result.ready,
        readiness_level=result.readiness_level,
        checks=result.checks,
        blocking_reasons=result.blocking_reasons,
        warnings=result.warnings,
    )


@router.post("/versions/{version_id}/promote-candidate", response_model=LifecycleTransitionResponse)
def promote_to_candidate(version_id: str, request: LifecycleTransitionRequest):
    try:
        result = _lifecycle.promote_to_candidate(version_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "lifecycle_error", "detail": str(exc)}})
    return LifecycleTransitionResponse(**result.__dict__)


@router.post("/versions/{version_id}/approve", response_model=LifecycleTransitionResponse)
def approve_version(version_id: str, request: LifecycleTransitionRequest):
    try:
        result = _lifecycle.approve(version_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "lifecycle_error", "detail": str(exc)}})
    return LifecycleTransitionResponse(**result.__dict__)


@router.post("/versions/{version_id}/activate", response_model=LifecycleTransitionResponse)
def activate_version(version_id: str, request: LifecycleTransitionRequest):
    try:
        gate = _gate.check(version_id)
        if not gate.can_activate:
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "activation_blocked", "reasons": gate.blocking_reasons}},
            )
        result = _lifecycle.activate(version_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "lifecycle_error", "detail": str(exc)}})
    return LifecycleTransitionResponse(**result.__dict__)


@router.post("/versions/{version_id}/deprecate", response_model=LifecycleTransitionResponse)
def deprecate_version(version_id: str, request: LifecycleTransitionRequest):
    try:
        result = _lifecycle.deprecate(version_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "lifecycle_error", "detail": str(exc)}})
    return LifecycleTransitionResponse(**result.__dict__)


@router.get("/versions/{version_id}/activation-gate", response_model=ActivationGateResponse)
def check_activation_gate(version_id: str):
    try:
        result = _gate.check(version_id)
    except ValueError as exc:
        return JSONResponse(status_code=404, content={"error": {"code": "not_found", "detail": str(exc)}})
    return ActivationGateResponse(
        version_id=result.version_id,
        can_activate=result.can_activate,
        gate_status=result.gate_status,
        checks=result.checks,
        blocking_reasons=result.blocking_reasons,
        warnings=result.warnings,
    )


@router.post("/versions/{version_id}/rollback-plan", response_model=RollbackPlanResponse)
def get_rollback_plan(version_id: str, body: dict):
    target_version_id = body.get("target_version_id", "")
    if not target_version_id:
        return JSONResponse(status_code=400, content={"error": {"code": "missing_target_version_id"}})
    try:
        result = _planner.plan(version_id, target_version_id)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "plan_error", "detail": str(exc)}})
    return RollbackPlanResponse(
        current_version_id=result.current_version_id,
        target_version_id=result.target_version_id,
        skill_id=result.skill_id,
        current_version_number=result.current_version_number,
        target_version_number=result.target_version_number,
        current_status=result.current_status,
        target_status=result.target_status,
        is_executable=result.is_executable,
        blocking_reasons=result.blocking_reasons,
        warnings=result.warnings,
        impact_summary=result.impact_summary,
        step_delta=result.step_delta,
    )


@router.post("/versions/{version_id}/rollback-to/{target_version_id}", response_model=RollbackResultResponse)
def execute_rollback(version_id: str, target_version_id: str, request: RollbackExecuteRequest):
    try:
        result = _rollback.execute(version_id, target_version_id, actor=request.actor, reason=request.reason)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "rollback_error", "detail": str(exc)}})
    return RollbackResultResponse(
        skill_id=result.skill_id,
        rolled_back_version_id=result.rolled_back_version_id,
        rolled_back_version_number=result.rolled_back_version_number,
        reactivated_version_id=result.reactivated_version_id,
        reactivated_version_number=result.reactivated_version_number,
        actor=result.actor,
        reason=result.reason,
    )


@router.get("/versions/{version_id}/lifecycle-audit", response_model=LifecycleAuditResponse)
def get_lifecycle_audit(version_id: str):
    result = _audit.get_events(version_id)
    if result is None:
        return JSONResponse(status_code=404, content={"error": {"code": "version_not_found", "version_id": version_id}})
    return LifecycleAuditResponse(
        version_id=result.version_id,
        skill_id=result.skill_id,
        current_status=result.current_status,
        version_number=result.version_number,
        events=[
            LifecycleEventEntryResponse(**e.__dict__)
            for e in result.events
        ],
    )


@router.post("/versions/compare", response_model=VersionComparisonResponse)
def compare_versions(request: CompareVersionsRequest):
    try:
        result = _comparator.compare(request.version_id_a, request.version_id_b)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": {"code": "compare_error", "detail": str(exc)}})
    return VersionComparisonResponse(
        version_id_a=result.version_id_a,
        version_id_b=result.version_id_b,
        version_number_a=result.version_number_a,
        version_number_b=result.version_number_b,
        steps_added=[StepDiffResponse(**d.__dict__) for d in result.steps_added],
        steps_removed=[StepDiffResponse(**d.__dict__) for d in result.steps_removed],
        steps_changed=[StepDiffResponse(**d.__dict__) for d in result.steps_changed],
        guards_added=result.guards_added,
        guards_removed=result.guards_removed,
        selectors_changed=result.selectors_changed,
        is_identical=result.is_identical,
        summary=result.summary,
    )
