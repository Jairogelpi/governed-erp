from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.outcomes import (
    CaptureFollowupRequest,
    MeasurementPlanApproveRequest,
    MeasurementPlanCreateRequest,
    MeasurementPlanResponse,
    OutcomeObservationResponse,
    RealizedOutcomeReportResponse,
)
from erpguard.application.outcomes.service import (
    OutcomeApprovalRejected,
    OutcomePlanNotFound,
    OutcomeService,
    OutcomeTransitionError,
    OutcomeValidationError,
)
from erpguard.domain.identity.auth import Principal
from erpguard.domain.outcomes.types import ObservedMetrics

measurement_plans_router = APIRouter(prefix="/v1/measurement-plans", tags=["outcomes"])
recommendation_plans_router = APIRouter(prefix="/v1/recommendations", tags=["outcomes"])
outcome_reports_router = APIRouter(prefix="/v1/outcome-reports", tags=["outcomes"])


@recommendation_plans_router.post(
    "/{recommendation_id}/measurement-plans", response_model=MeasurementPlanResponse, status_code=status.HTTP_201_CREATED
)
def create_measurement_plan(
    recommendation_id: str,
    request: MeasurementPlanCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> MeasurementPlanResponse:
    try:
        row = OutcomeService(db).create_plan(
            tenant_id=principal.tenant_id,
            recommendation_id=recommendation_id,
            execution_run_ids=request.execution_run_ids,
            comparison_method=request.comparison_method,
            observation_start=request.observation_start,
            observation_end=request.observation_end,
            created_by=principal.user_id,
            minimum_data_coverage=request.minimum_data_coverage,
            target_metrics=request.target_metrics or None,
            assumptions=request.assumptions or None,
        )
    except OutcomeValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _plan_response(row)


@measurement_plans_router.get("/{plan_id}", response_model=MeasurementPlanResponse)
def get_measurement_plan(
    plan_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> MeasurementPlanResponse:
    try:
        row = OutcomeService(db).get(tenant_id=principal.tenant_id, plan_id=plan_id)
    except OutcomePlanNotFound as exc:
        raise HTTPException(status_code=404, detail="measurement_plan_not_found") from exc
    return _plan_response(row)


@measurement_plans_router.post("/{plan_id}/approve", response_model=MeasurementPlanResponse)
def approve_measurement_plan(
    plan_id: str,
    request: MeasurementPlanApproveRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> MeasurementPlanResponse:
    try:
        row = OutcomeService(db).approve_plan(
            tenant_id=principal.tenant_id, plan_id=plan_id, approval_id=request.approval_id,
            approver_actor_id=principal.user_id,
        )
    except OutcomePlanNotFound as exc:
        raise HTTPException(status_code=404, detail="measurement_plan_not_found") from exc
    except (OutcomeApprovalRejected, OutcomeTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _plan_response(row)


@measurement_plans_router.post("/{plan_id}/start", response_model=MeasurementPlanResponse)
def start_measurement_plan(
    plan_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("operator"))
) -> MeasurementPlanResponse:
    try:
        row = OutcomeService(db).start(tenant_id=principal.tenant_id, plan_id=plan_id)
    except OutcomePlanNotFound as exc:
        raise HTTPException(status_code=404, detail="measurement_plan_not_found") from exc
    except OutcomeTransitionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _plan_response(row)


@measurement_plans_router.post("/{plan_id}/capture-followup", response_model=OutcomeObservationResponse)
def capture_followup(
    plan_id: str,
    request: CaptureFollowupRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> OutcomeObservationResponse:
    service = OutcomeService(db)
    try:
        if request.followup_snapshot_id is not None and request.followup_analysis_id is not None:
            row = service.capture_followup_live(
                tenant_id=principal.tenant_id, plan_id=plan_id,
                followup_snapshot_id=request.followup_snapshot_id,
                followup_analysis_id=request.followup_analysis_id,
                created_by=principal.user_id,
            )
        elif request.observed is not None:
            observed = ObservedMetrics.model_validate(request.observed.model_dump(mode="json"))
            row = service.capture_followup_fixture(
                tenant_id=principal.tenant_id, plan_id=plan_id, observed=observed,
                created_by=principal.user_id, source=request.source,
            )
        else:
            raise HTTPException(status_code=400, detail="observed_or_followup_ids_required")
    except OutcomePlanNotFound as exc:
        raise HTTPException(status_code=404, detail="measurement_plan_not_found") from exc
    except (OutcomeValidationError, OutcomeTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _observation_response(row)


@measurement_plans_router.post("/{plan_id}/evaluate", response_model=RealizedOutcomeReportResponse)
def evaluate_measurement_plan(
    plan_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("operator"))
) -> RealizedOutcomeReportResponse:
    try:
        report = OutcomeService(db).evaluate(tenant_id=principal.tenant_id, plan_id=plan_id, created_by=principal.user_id)
    except OutcomePlanNotFound as exc:
        raise HTTPException(status_code=404, detail="measurement_plan_not_found") from exc
    except (OutcomeValidationError, OutcomeTransitionError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _report_response(report)


@outcome_reports_router.get("/{report_id}", response_model=RealizedOutcomeReportResponse)
def get_outcome_report(
    report_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> RealizedOutcomeReportResponse:
    from erpguard.db.model_packages.outcomes import RealizedOutcomeReport

    row = db.query(RealizedOutcomeReport).filter_by(tenant_id=principal.tenant_id, id=report_id).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="outcome_report_not_found")
    return _report_response(row)


def _plan_response(row) -> MeasurementPlanResponse:
    return MeasurementPlanResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        recommendation_id=row.recommendation_id,
        margin_opportunity_id=row.margin_opportunity_id,
        baseline_snapshot_id=row.baseline_snapshot_id,
        baseline_analysis_id=row.baseline_analysis_id,
        action_draft_id=row.action_draft_id,
        execution_run_ids=json.loads(row.execution_run_ids_json),
        metric_definition_version=row.metric_definition_version,
        target_metrics=json.loads(row.target_metrics_json),
        comparison_method=row.comparison_method,
        observation_start=row.observation_start,
        observation_end=row.observation_end,
        minimum_data_coverage=row.minimum_data_coverage,
        status=row.status,
        content_hash=row.content_hash,
        approval_scope=OutcomeService.approval_scope(row),
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
        started_at=row.started_at.isoformat() if row.started_at else None,
        ready_at=row.ready_at.isoformat() if row.ready_at else None,
        evaluated_at=row.evaluated_at.isoformat() if row.evaluated_at else None,
    )


def _observation_response(row) -> OutcomeObservationResponse:
    return OutcomeObservationResponse(
        id=row.id,
        measurement_plan_id=row.measurement_plan_id,
        followup_snapshot_id=row.followup_snapshot_id,
        followup_analysis_id=row.followup_analysis_id,
        source=row.source,
        observed_at=row.observed_at.isoformat(),
        metrics=json.loads(row.metrics_json),
        created_at=row.created_at.isoformat(),
    )


def _report_response(row) -> RealizedOutcomeReportResponse:
    return RealizedOutcomeReportResponse(
        id=row.id,
        measurement_plan_id=row.measurement_plan_id,
        recommendation_id=row.recommendation_id,
        opportunity_id=row.opportunity_id,
        estimated_conservative=row.estimated_conservative,
        estimated_base=row.estimated_base,
        estimated_optimistic=row.estimated_optimistic,
        observed_revenue_change=row.observed_revenue_change,
        observed_margin_change=row.observed_margin_change,
        observed_margin_percent_change=row.observed_margin_percent_change,
        observed_refund_change=row.observed_refund_change,
        realized_value=row.realized_value,
        variance_from_base_estimate=row.variance_from_base_estimate,
        result_classification=row.result_classification,
        confidence_band=row.confidence_band,
        limitations=json.loads(row.limitations_json),
        assumptions=json.loads(row.assumptions_json),
        metric_definition_version=row.metric_definition_version,
        content_hash=row.content_hash,
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
    )
