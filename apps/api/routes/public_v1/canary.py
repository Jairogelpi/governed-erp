from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.canary import (
    CanaryIncidentCreateRequest,
    CanaryIncidentResolveRequest,
    CanaryIncidentResponse,
    CanaryPolicyApproveRequest,
    CanaryPolicyCreateRequest,
    CanaryPolicyResponse,
    CanaryRoutingDecisionResponse,
)
from erpguard.application.canary.service import (
    CanaryApprovalRejected,
    CanaryPolicyNotFound,
    CanaryRouterService,
    CanaryTransitionError,
    CanaryValidationError,
)
from erpguard.domain.identity.auth import Principal

router = APIRouter(prefix="/v1/canary-policies", tags=["canary"])


@router.post("", response_model=CanaryPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_canary_policy(
    request: CanaryPolicyCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> CanaryPolicyResponse:
    try:
        row = CanaryRouterService(db).create_policy(
            tenant_id=principal.tenant_id,
            process_key=request.process_key,
            stable_skill_package_id=request.stable_skill_package_id,
            canary_skill_package_id=request.canary_skill_package_id,
            shadow_deployment_id=request.shadow_deployment_id,
            percentage_basis_points=request.percentage_basis_points,
            maximum_cases=request.maximum_cases,
            maximum_total_amount=request.maximum_total_amount,
            allowed_capabilities=request.allowed_capabilities,
            maximum_amount=request.maximum_amount,
            created_by=principal.user_id,
            company_ids=request.company_ids,
            minimum_amount=request.minimum_amount,
            object_types=request.object_types,
            safety_thresholds=request.safety_thresholds,
        )
    except CanaryValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _policy_response(row)


@router.get("/{policy_id}", response_model=CanaryPolicyResponse)
def get_canary_policy(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> CanaryPolicyResponse:
    try:
        row = CanaryRouterService(db).get(tenant_id=principal.tenant_id, policy_id=policy_id)
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc
    return _policy_response(row)


@router.post("/{policy_id}/approve", response_model=CanaryPolicyResponse)
def approve_canary_policy(
    policy_id: str,
    request: CanaryPolicyApproveRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> CanaryPolicyResponse:
    try:
        row = CanaryRouterService(db).approve_policy(
            tenant_id=principal.tenant_id, policy_id=policy_id, approval_id=request.approval_id,
            approver_actor_id=principal.user_id,
        )
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc
    except (CanaryApprovalRejected, CanaryTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _policy_response(row)


@router.post("/{policy_id}/activate", response_model=CanaryPolicyResponse)
def activate_canary_policy(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("admin"))
) -> CanaryPolicyResponse:
    try:
        row = CanaryRouterService(db).activate(tenant_id=principal.tenant_id, policy_id=policy_id)
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc
    except (CanaryValidationError, CanaryTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _policy_response(row)


@router.post("/{policy_id}/pause", response_model=CanaryPolicyResponse)
def pause_canary_policy(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("admin"))
) -> CanaryPolicyResponse:
    try:
        row = CanaryRouterService(db).pause(tenant_id=principal.tenant_id, policy_id=policy_id)
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc
    except CanaryTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _policy_response(row)


@router.post("/{policy_id}/resume", response_model=CanaryPolicyResponse)
def resume_canary_policy(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("admin"))
) -> CanaryPolicyResponse:
    try:
        row = CanaryRouterService(db).resume(tenant_id=principal.tenant_id, policy_id=policy_id)
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc
    except CanaryTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _policy_response(row)


@router.post("/{policy_id}/abort", response_model=CanaryPolicyResponse)
def abort_canary_policy(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("admin"))
) -> CanaryPolicyResponse:
    try:
        row = CanaryRouterService(db).abort(tenant_id=principal.tenant_id, policy_id=policy_id)
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc
    except CanaryTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _policy_response(row)


@router.post("/{policy_id}/complete", response_model=CanaryPolicyResponse)
def complete_canary_policy(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("admin"))
) -> CanaryPolicyResponse:
    try:
        row = CanaryRouterService(db).complete(tenant_id=principal.tenant_id, policy_id=policy_id)
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc
    except CanaryTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _policy_response(row)


@router.get("/{policy_id}/dashboard")
def get_canary_dashboard(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> dict:
    try:
        return CanaryRouterService(db).dashboard(tenant_id=principal.tenant_id, policy_id=policy_id)
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc


@router.get("/{policy_id}/routing-decisions", response_model=list[CanaryRoutingDecisionResponse])
def list_routing_decisions(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> list[CanaryRoutingDecisionResponse]:
    rows = CanaryRouterService(db).list_routing_decisions(tenant_id=principal.tenant_id, policy_id=policy_id)
    return [_routing_decision_response(row) for row in rows]


@router.get("/{policy_id}/incidents", response_model=list[CanaryIncidentResponse])
def list_incidents(
    policy_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> list[CanaryIncidentResponse]:
    rows = CanaryRouterService(db).list_incidents(tenant_id=principal.tenant_id, policy_id=policy_id)
    return [_incident_response(row) for row in rows]


@router.post("/{policy_id}/incidents", response_model=CanaryIncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(
    policy_id: str,
    request: CanaryIncidentCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> CanaryIncidentResponse:
    try:
        row = CanaryRouterService(db).record_incident(
            tenant_id=principal.tenant_id, policy_id=policy_id, incident_type=request.incident_type,
            severity=request.severity, details=request.details,
            routing_decision_id=request.routing_decision_id, execution_run_id=request.execution_run_id,
        )
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_policy_not_found") from exc
    return _incident_response(row)


@router.post("/incidents/{incident_id}/resolve", response_model=CanaryIncidentResponse)
def resolve_incident(
    incident_id: str,
    request: CanaryIncidentResolveRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> CanaryIncidentResponse:
    try:
        row = CanaryRouterService(db).resolve_incident(
            tenant_id=principal.tenant_id, incident_id=incident_id, resolved_by=principal.user_id,
            resolution_notes=request.resolution_notes,
        )
    except CanaryPolicyNotFound as exc:
        raise HTTPException(status_code=404, detail="canary_incident_not_found") from exc
    return _incident_response(row)


def _policy_response(row) -> CanaryPolicyResponse:
    return CanaryPolicyResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        process_key=row.process_key,
        stable_skill_package_id=row.stable_skill_package_id,
        canary_skill_package_id=row.canary_skill_package_id,
        shadow_deployment_id=row.shadow_deployment_id,
        status=row.status,
        percentage_basis_points=row.percentage_basis_points,
        maximum_cases=row.maximum_cases,
        maximum_total_amount=row.maximum_total_amount,
        allowed_capabilities=json.loads(row.allowed_capabilities_json),
        company_ids=json.loads(row.company_ids_json),
        minimum_amount=row.minimum_amount,
        maximum_amount=row.maximum_amount,
        object_types=json.loads(row.object_types_json),
        safety_thresholds=json.loads(row.safety_thresholds_json),
        content_hash=row.content_hash,
        approval_scope=CanaryRouterService.approval_scope(row),
        created_by=row.created_by,
        approved_by=row.approved_by,
        created_at=row.created_at.isoformat(),
        activated_at=row.activated_at.isoformat() if row.activated_at else None,
        paused_at=row.paused_at.isoformat() if row.paused_at else None,
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        aborted_at=row.aborted_at.isoformat() if row.aborted_at else None,
    )


def _routing_decision_response(row) -> CanaryRoutingDecisionResponse:
    return CanaryRoutingDecisionResponse(
        id=row.id,
        canary_policy_id=row.canary_policy_id,
        process_key=row.process_key,
        business_object_key=row.business_object_key,
        bucket=row.bucket,
        selected_lane=row.selected_lane,
        selected_skill_package_id=row.selected_skill_package_id,
        selection_reason=row.selection_reason,
        execution_run_id=row.execution_run_id,
        created_at=row.created_at.isoformat(),
    )


def _incident_response(row) -> CanaryIncidentResponse:
    return CanaryIncidentResponse(
        id=row.id,
        canary_policy_id=row.canary_policy_id,
        incident_type=row.incident_type,
        severity=row.severity,
        details=json.loads(row.details_json),
        created_at=row.created_at.isoformat(),
        resolved_at=row.resolved_at.isoformat() if row.resolved_at else None,
        resolved_by=row.resolved_by,
        resolution_notes=row.resolution_notes,
    )
