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
    ShadowFeedProcessRequest,
    ShadowFeedProcessResponse,
    ShadowOutcomeRequest,
    ShadowOutcomeResponse,
    ShadowReviewRequest,
    ShadowReviewResponse,
)
from erpguard.domain.identity.auth import Principal
from erpguard.domain.shadow.operational_feed import OperationalShadowFeedService
from erpguard.domain.shadow.service import ShadowNotFound, ShadowService, ShadowValidationError
from erpguard.domain.shadow.types import ShadowEvaluationInput, ShadowOutcomeInput


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
            minimum_case_count=request.minimum_case_count,
            minimum_decision_coverage=request.minimum_decision_coverage,
            minimum_review_coverage=request.minimum_review_coverage,
            minimum_outcome_reconciliation=request.minimum_outcome_reconciliation,
            observation_window_hours=request.observation_window_hours,
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


@router.post(
    "/{deployment_id}/feed/process",
    response_model=ShadowFeedProcessResponse,
    status_code=status.HTTP_201_CREATED,
)
def process_shadow_feed(
    deployment_id: str,
    request: ShadowFeedProcessRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ShadowFeedProcessResponse:
    try:
        summary = OperationalShadowFeedService(db).process_deployment(
            tenant_id=principal.tenant_id,
            deployment_id=deployment_id,
            requested_case_ids=request.case_ids,
            trigger="api",
            created_by=principal.user_id,
        )
        return ShadowFeedProcessResponse(
            feed_run_id=summary.feed_run_id,
            deployment_id=summary.deployment_id,
            scanned_case_count=summary.scanned_case_count,
            evaluated_case_count=summary.evaluated_case_count,
            deduplicated_case_count=summary.deduplicated_case_count,
            failed_case_count=summary.failed_case_count,
            failure_codes=list(summary.failure_codes),
            no_effects=summary.no_effects,
        )
    except ShadowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@router.post(
    "/{deployment_id}/cases/{case_result_id}/outcomes",
    response_model=ShadowOutcomeResponse,
    status_code=status.HTTP_201_CREATED,
)
def reconcile_shadow_outcome(
    deployment_id: str,
    case_result_id: str,
    request: ShadowOutcomeRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ShadowOutcomeResponse:
    try:
        outcome = ShadowOutcomeInput.model_validate(request.model_dump())
        row = ShadowService(db).add_outcome(
            tenant_id=principal.tenant_id,
            deployment_id=deployment_id,
            case_result_id=case_result_id,
            recorded_by=principal.user_id,
            outcome=outcome,
        )
        return _outcome_response(row)
    except ShadowNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc
    except ShadowValidationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{deployment_id}/dashboard", response_model=ShadowDashboardResponse)
def get_shadow_dashboard(
    deployment_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ShadowDashboardResponse:
    try:
        service = ShadowService(db)
        deployment = service.get_deployment(
            tenant_id=principal.tenant_id,
            deployment_id=deployment_id,
        )
        canonical_count = OperationalShadowFeedService(db).canonical_case_count(
            tenant_id=principal.tenant_id,
            object_type=deployment.object_type,
        )
        return ShadowDashboardResponse(
            **service.dashboard(
                tenant_id=principal.tenant_id,
                deployment_id=deployment_id,
                canonical_case_count=canonical_count,
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
        reference_version=row.active_version,
        minimum_case_count=row.minimum_case_count,
        minimum_decision_coverage=row.minimum_decision_coverage,
        minimum_review_coverage=row.minimum_review_coverage,
        minimum_outcome_reconciliation=row.minimum_outcome_reconciliation,
        observation_window_hours=row.observation_window_hours,
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


def _outcome_response(row) -> ShadowOutcomeResponse:
    return ShadowOutcomeResponse(
        id=row.id,
        recorded_by=row.recorded_by,
        outcome=json.loads(row.outcome_json),
        observed_decision_status=row.observed_decision_status,
        provenance=row.provenance,
        source_event_ids=json.loads(row.source_event_ids_json),
        observed_at=row.observed_at.isoformat(),
        deterministic_hash=row.deterministic_hash,
        created_at=row.created_at.isoformat(),
    )


def _case_response(service: ShadowService, tenant_id: str, row) -> ShadowCaseResponse:
    reviews = service.reviews_for_case(
        tenant_id=tenant_id,
        deployment_id=row.deployment_id,
        case_result_id=row.id,
    )
    review_responses = [_review_response(review) for review in reviews]
    outcomes = service.outcomes_for_case(
        tenant_id=tenant_id,
        deployment_id=row.deployment_id,
        case_result_id=row.id,
    )
    outcome_responses = [_outcome_response(outcome) for outcome in outcomes]
    inline_outcome = json.loads(row.actual_outcome_json) if row.actual_outcome_json else None
    latest_outcome = outcome_responses[-1] if outcome_responses else None
    return ShadowCaseResponse(
        id=row.id,
        deployment_id=row.deployment_id,
        case_id=row.case_id,
        active_decision=json.loads(row.active_decision_json),
        candidate_decision=json.loads(row.candidate_decision_json),
        agreement=row.agreement,
        difference_categories=json.loads(row.difference_categories_json),
        actual_outcome=latest_outcome.outcome if latest_outcome else inline_outcome,
        actual_outcome_provenance=latest_outcome.provenance if latest_outcome else None,
        outcome_observations=outcome_responses,
        reviewer_label=review_responses[-1].label if review_responses else None,
        reviews=review_responses,
        evaluation_mode=row.evaluation_mode,
        canonical_trace_hash=row.canonical_trace_hash,
        trace_provenance=json.loads(row.trace_provenance_json),
        variant_id=row.variant_id,
        event_count=row.event_count,
        first_event_at=row.first_event_at,
        last_event_at=row.last_event_at,
        deterministic_hash=row.deterministic_hash,
        evaluated_at=row.evaluated_at.isoformat(),
    )
