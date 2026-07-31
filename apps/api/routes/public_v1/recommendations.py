from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.recommendations import (
    ActionDraftCreateRequest,
    ActionDraftPlanRunRequest,
    ActionDraftResponse,
    RecommendationApproveRequest,
    RecommendationCreateRequest,
    RecommendationResponse,
)
from erpguard.application.recommendations.service import (
    ActionDraftNotFound,
    ApprovalRejected,
    NoActiveSkillForActionTemplate,
    OpportunityBlocked,
    RecommendationNotFound,
    RecommendationService,
    RecommendationValidationError,
)
from erpguard.domain.execution.permit_service import RunValidationError
from erpguard.domain.identity.auth import Principal
from erpguard.domain.recommendations.state_machine import InvalidTransition
from erpguard.domain.recommendations.types import PricingScenarioInputs

opportunities_router = APIRouter(prefix="/v1/opportunities", tags=["recommendations"])
router = APIRouter(prefix="/v1/recommendations", tags=["recommendations"])
action_drafts_router = APIRouter(prefix="/v1/action-drafts", tags=["recommendations"])


@opportunities_router.post(
    "/{opportunity_id}/recommendations", response_model=RecommendationResponse, status_code=status.HTTP_201_CREATED
)
def create_recommendation(
    opportunity_id: str,
    request: RecommendationCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> RecommendationResponse:
    try:
        row = RecommendationService(db).create(
            tenant_id=principal.tenant_id,
            opportunity_id=opportunity_id,
            recommendation_type=request.recommendation_type,
            title=request.title,
            selected_action_template=request.selected_action_template,
            created_by=principal.user_id,
        )
    except OpportunityBlocked as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RecommendationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _recommendation_response(row)


@router.get("/{recommendation_id}", response_model=RecommendationResponse)
def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> RecommendationResponse:
    try:
        row = RecommendationService(db).get(tenant_id=principal.tenant_id, recommendation_id=recommendation_id)
    except RecommendationNotFound as exc:
        raise HTTPException(status_code=404, detail="recommendation_not_found") from exc
    return _recommendation_response(row)


@router.post("/{recommendation_id}/submit", response_model=RecommendationResponse)
def submit_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> RecommendationResponse:
    try:
        row = RecommendationService(db).submit(tenant_id=principal.tenant_id, recommendation_id=recommendation_id)
    except RecommendationNotFound as exc:
        raise HTTPException(status_code=404, detail="recommendation_not_found") from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _recommendation_response(row)


@router.post("/{recommendation_id}/approve", response_model=RecommendationResponse)
def approve_recommendation(
    recommendation_id: str,
    request: RecommendationApproveRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> RecommendationResponse:
    try:
        row = RecommendationService(db).approve(
            tenant_id=principal.tenant_id,
            recommendation_id=recommendation_id,
            approval_id=request.approval_id,
            approver_actor_id=principal.user_id,
        )
    except RecommendationNotFound as exc:
        raise HTTPException(status_code=404, detail="recommendation_not_found") from exc
    except (ApprovalRejected, InvalidTransition) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _recommendation_response(row)


@router.post("/{recommendation_id}/reject", response_model=RecommendationResponse)
def reject_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> RecommendationResponse:
    try:
        row = RecommendationService(db).reject(tenant_id=principal.tenant_id, recommendation_id=recommendation_id)
    except RecommendationNotFound as exc:
        raise HTTPException(status_code=404, detail="recommendation_not_found") from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _recommendation_response(row)


@router.post(
    "/{recommendation_id}/action-drafts", response_model=ActionDraftResponse, status_code=status.HTTP_201_CREATED
)
def create_action_draft(
    recommendation_id: str,
    request: ActionDraftCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ActionDraftResponse:
    pricing_inputs = (
        PricingScenarioInputs.model_validate(request.pricing_inputs.model_dump(mode="json"))
        if request.pricing_inputs is not None
        else None
    )
    try:
        row = RecommendationService(db).create_action_draft(
            tenant_id=principal.tenant_id,
            recommendation_id=recommendation_id,
            process_key=request.process_key,
            connection_id=request.connection_id,
            pricing_inputs=pricing_inputs,
            created_by=principal.user_id,
        )
    except RecommendationNotFound as exc:
        raise HTTPException(status_code=404, detail="recommendation_not_found") from exc
    except RecommendationValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _action_draft_response(row)


@action_drafts_router.get("/{action_draft_id}", response_model=ActionDraftResponse)
def get_action_draft(
    action_draft_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ActionDraftResponse:
    try:
        row = RecommendationService(db).get_action_draft(tenant_id=principal.tenant_id, action_draft_id=action_draft_id)
    except ActionDraftNotFound as exc:
        raise HTTPException(status_code=404, detail="action_draft_not_found") from exc
    return _action_draft_response(row)


@action_drafts_router.post("/{action_draft_id}/validate", response_model=ActionDraftResponse)
def validate_action_draft(
    action_draft_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ActionDraftResponse:
    try:
        row = RecommendationService(db).validate_action_draft(tenant_id=principal.tenant_id, action_draft_id=action_draft_id)
    except ActionDraftNotFound as exc:
        raise HTTPException(status_code=404, detail="action_draft_not_found") from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _action_draft_response(row)


@action_drafts_router.post("/{action_draft_id}/plan-run", response_model=ActionDraftResponse)
def plan_run_action_draft(
    action_draft_id: str,
    request: ActionDraftPlanRunRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ActionDraftResponse:
    service = RecommendationService(db)
    try:
        row = service.get_action_draft(tenant_id=principal.tenant_id, action_draft_id=action_draft_id)
        if row.status == "validated":
            row = service.mark_ready_for_run(tenant_id=principal.tenant_id, action_draft_id=action_draft_id)
        row = service.convert_to_run(
            tenant_id=principal.tenant_id,
            action_draft_id=action_draft_id,
            actor_id=principal.user_id,
            idempotency_key=request.idempotency_key,
        )
    except ActionDraftNotFound as exc:
        raise HTTPException(status_code=404, detail="action_draft_not_found") from exc
    except NoActiveSkillForActionTemplate as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (RecommendationValidationError, InvalidTransition, RunValidationError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _action_draft_response(row)


@action_drafts_router.post("/{action_draft_id}/invalidate", response_model=ActionDraftResponse)
def invalidate_action_draft(
    action_draft_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> ActionDraftResponse:
    try:
        row = RecommendationService(db).invalidate_action_draft(tenant_id=principal.tenant_id, action_draft_id=action_draft_id)
    except ActionDraftNotFound as exc:
        raise HTTPException(status_code=404, detail="action_draft_not_found") from exc
    except InvalidTransition as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _action_draft_response(row)


def _recommendation_response(row) -> RecommendationResponse:
    return RecommendationResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        margin_opportunity_id=row.margin_opportunity_id,
        margin_analysis_id=row.margin_analysis_id,
        snapshot_id=row.snapshot_id,
        recommendation_type=row.recommendation_type,
        title=row.title,
        business_rationale=json.loads(row.business_rationale_json),
        affected_population=json.loads(row.affected_population_json),
        estimated_impact_conservative=row.estimated_impact_conservative,
        estimated_impact_base=row.estimated_impact_base,
        estimated_impact_optimistic=row.estimated_impact_optimistic,
        confidence_band=row.confidence_band,
        risk_level=row.risk_level,
        selected_action_template=row.selected_action_template,
        status=row.status,
        source_content_hash=row.source_content_hash,
        content_hash=row.content_hash,
        approval_scope=RecommendationService.approval_scope(row),
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
        submitted_at=row.submitted_at.isoformat() if row.submitted_at else None,
        approved_at=row.approved_at.isoformat() if row.approved_at else None,
        converted_at=row.converted_at.isoformat() if row.converted_at else None,
    )


def _action_draft_response(row) -> ActionDraftResponse:
    return ActionDraftResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        recommendation_id=row.recommendation_id,
        action_template=row.action_template,
        action_template_version=row.action_template_version,
        connector_id=row.connector_id,
        process_key=row.process_key,
        capability=row.capability,
        connection_id=row.connection_id,
        arguments=json.loads(row.arguments_json),
        constraints=json.loads(row.constraints_json),
        execution_classification=row.execution_classification,
        status=row.status,
        content_hash=row.content_hash,
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
        validated_at=row.validated_at.isoformat() if row.validated_at else None,
        converted_run_id=row.converted_run_id,
        invalidated_at=row.invalidated_at.isoformat() if row.invalidated_at else None,
    )
