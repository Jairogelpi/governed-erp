"""Phase 18 shadow deployment and comparison API."""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.shadow import (
    ShadowCaseEvaluateRequest,
    ShadowCaseResponse,
    ShadowDashboardResponse,
    ShadowDeploymentCreateRequest,
    ShadowDeploymentResponse,
    ShadowReviewRequest,
    ShadowReviewResponse,
)
from erpguard.domain.identity.auth import Principal
from erpguard.domain.shadow.service import ShadowNotFound, ShadowService, ShadowValidationError
from erpguard.domain.shadow.types import ShadowEvaluationInput


router = APIRouter(prefix="/v1/deployments", tags=["shadow"])


@router.post(
    "/shadow",
    response_model=ShadowDeploymentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_shadow_deployment(
    request: ShadowDeploymentCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> ShadowDeploymentResponse:
    try:
        row = ShadowService(db).create_deployment(
            tenant_id=principal.tenant_id,
            candidate_id=request.candidate_id,
            proof_id=request.proof_id,
            object_type=request.object_type,
            agreement_threshold=request.agreement_threshold,
            created_by=principal.user_id,
        )
    except ShadowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ShadowValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _deployment_response(row)


@router.get("/{deployment_id}", response_model=ShadowDeploymentResponse)
def get_shadow_deployment(
    deployment_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ShadowDeploymentResponse:
    try:
        return _deployment_response(
            ShadowService(db).get_deployment(
                tenant_id=principal.tenant_id,
                deployment_id=deployment_id,
            )
        )
    except ShadowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@router.post(
    "/{deployment_id}/cases",
    response_model=ShadowCaseResponse,
    status_code=status.HTTP_201_CREATED,
)
def evaluate_shadow_case(
    deployment_id: str,
    request: ShadowCaseEvaluateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ShadowCaseResponse:
    service = ShadowService(db)
    try:
        row = service.evaluate_case(
            tenant_id=principal.tenant_id,
            deployment_id=deployment_id,
            evaluation=ShadowEvaluationInput.model_validate(request.model_dump()),
        )
        return _case_response(service, principal.tenant_id, row)
    except ShadowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ShadowValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{deployment_id}/cases", response_model=list[ShadowCaseResponse])
def list_shadow_cases(
    deployment_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> list[ShadowCaseResponse]:
    service = ShadowService(db)
    try:
        rows = service.list_cases(
            tenant_id=principal.tenant_id,
            deployment_id=deployment_id,
        )
        return [_case_response(service, principal.tenant_id, row) for row in rows]
    except ShadowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@router.post(
    "/{deployment_id}/cases/{case_result_id}/reviews",
    response_model=ShadowReviewResponse,
    status_code=status.HTTP_201_CREATED,
)
def review_shadow_case(
    deployment_id: str,
    case_result_id: str,
    request: ShadowReviewRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> ShadowReviewResponse:
    try:
        row = ShadowService(db).add_review(
            tenant_id=principal.tenant_id,
            deployment_id=deployment_id,
            case_result_id=case_result_id,
            reviewer_id=principal.user_id,
            label=request.label,
            notes=request.notes,
        )
    except ShadowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    return _review_response(row)


@router.get("/{deployment_id}/dashboard", response_model=ShadowDashboardResponse)
def get_shadow_dashboard(
    deployment_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ShadowDashboardResponse:
    try:
        return ShadowDashboardResponse(
            **ShadowService(db).dashboard(
                tenant_id=principal.tenant_id,
                deployment_id=deployment_id,
            )
        )
    except ShadowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


def _deployment_response(row) -> ShadowDeploymentResponse:
    return ShadowDeploymentResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        candidate_id=row.candidate_id,
        proof_id=row.proof_id,
        process_key=row.process_key,
        active_version=row.active_version,
        candidate_version=row.candidate_version,
        object_type=row.object_type,
        status=row.status,
        agreement_threshold=row.agreement_threshold,
        no_effects=row.no_effects,
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
    )


def _review_response(row) -> ShadowReviewResponse:
    return ShadowReviewResponse(
        id=row.id,
        reviewer_id=row.reviewer_id,
        label=row.label,
        notes=row.notes,
        created_at=row.created_at.isoformat(),
    )


def _case_response(service: ShadowService, tenant_id: str, row) -> ShadowCaseResponse:
    reviews = service.reviews_for_case(
        tenant_id=tenant_id,
        deployment_id=row.deployment_id,
        case_result_id=row.id,
    )
    review_responses = [_review_response(review) for review in reviews]
    return ShadowCaseResponse(
        id=row.id,
        deployment_id=row.deployment_id,
        case_id=row.case_id,
        active_decision=json.loads(row.active_decision_json),
        candidate_decision=json.loads(row.candidate_decision_json),
        agreement=row.agreement,
        difference_categories=json.loads(row.difference_categories_json),
        actual_outcome=json.loads(row.actual_outcome_json) if row.actual_outcome_json else None,
        reviewer_label=review_responses[-1].label if review_responses else None,
        reviews=review_responses,
        deterministic_hash=row.deterministic_hash,
        evaluated_at=row.evaluated_at.isoformat(),
    )
