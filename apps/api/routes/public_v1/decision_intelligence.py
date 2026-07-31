from __future__ import annotations

import json
from collections.abc import Callable
from decimal import Decimal
from typing import cast

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.decision_intelligence import (
    AnalyticalSnapshotCreateRequest,
    AnalyticalSnapshotResponse,
    DataQualityResponse,
    MarginAnalysisCreateRequest,
    MarginAnalysisResponse,
)
from erpguard.application.connectors.service import (
    ConnectionNotFound,
    ConnectorApplicationService,
    ConnectorApplicationError,
)
from erpguard.application.decision_intelligence.analysis_service import (
    DecisionIntelligenceNotFound,
    DecisionIntelligenceService,
    DecisionIntelligenceValidationError,
)
from erpguard.application.decision_intelligence.extraction_service import (
    OdooAnalyticalExtractor,
)
from erpguard.connectors.odoo.transports import OdooReadTransport
from erpguard.connectors.sdk.models import ConnectorContext
from erpguard.domain.identity.auth import Principal


router = APIRouter(
    prefix="/v1/decision-intelligence",
    tags=["decision-intelligence"],
)


@router.post(
    "/snapshots",
    response_model=AnalyticalSnapshotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_analytical_snapshot(
    request: AnalyticalSnapshotCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> AnalyticalSnapshotResponse:
    try:
        _, context = ConnectorApplicationService(db).connection_context(
            tenant_id=principal.tenant_id,
            connection_id=request.connection_id,
            connector_id="odoo",
        )
        factory = cast(
            Callable[[ConnectorContext], OdooReadTransport],
            context.services["transport_factory"],
        )
        snapshot, report = DecisionIntelligenceService(db).create_snapshot(
            tenant_id=principal.tenant_id,
            connection_id=request.connection_id,
            company_ids=request.company_ids,
            period_start=request.period_start,
            period_end=request.period_end,
            comparison_period_start=request.comparison_period_start,
            comparison_period_end=request.comparison_period_end,
            max_rows_per_model=request.max_rows_per_model,
            minimum_cost_coverage=request.minimum_cost_coverage,
            created_by=principal.user_id,
            extractor=OdooAnalyticalExtractor(factory(context)),
        )
        return _snapshot_response(snapshot, report)
    except ConnectionNotFound as exc:
        raise HTTPException(status_code=404, detail="connection_not_found") from exc
    except (ConnectorApplicationError, KeyError, RuntimeError) as exc:
        raise HTTPException(
            status_code=503,
            detail="analytical_read_transport_unavailable",
        ) from exc
    except DecisionIntelligenceValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get(
    "/snapshots/{snapshot_id}",
    response_model=AnalyticalSnapshotResponse,
)
def get_analytical_snapshot(
    snapshot_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> AnalyticalSnapshotResponse:
    try:
        snapshot, report = DecisionIntelligenceService(db).get_snapshot(
            tenant_id=principal.tenant_id,
            snapshot_id=snapshot_id,
        )
        return _snapshot_response(snapshot, report)
    except DecisionIntelligenceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@router.post(
    "/snapshots/{snapshot_id}/margin-analysis",
    response_model=MarginAnalysisResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_margin_analysis(
    snapshot_id: str,
    request: MarginAnalysisCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> MarginAnalysisResponse:
    try:
        row = DecisionIntelligenceService(db).analyze_margin(
            tenant_id=principal.tenant_id,
            snapshot_id=snapshot_id,
            created_by=principal.user_id,
            tolerance=Decimal(str(request.tolerance)),
        )
        return _analysis_response(row)
    except DecisionIntelligenceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


@router.get(
    "/analyses/{analysis_id}",
    response_model=MarginAnalysisResponse,
)
def get_margin_analysis(
    analysis_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> MarginAnalysisResponse:
    try:
        return _analysis_response(
            DecisionIntelligenceService(db).get_analysis(
                tenant_id=principal.tenant_id,
                analysis_id=analysis_id,
            )
        )
    except DecisionIntelligenceNotFound as exc:
        raise HTTPException(status_code=404, detail=str(exc.args[0])) from exc


def _quality_response(report) -> DataQualityResponse:
    return DataQualityResponse(
        id=report.id,
        checks=json.loads(report.checks_json),
        errors=json.loads(report.errors_json),
        warnings=json.loads(report.warnings_json),
        cost_coverage_rate=report.cost_coverage_rate,
        revenue_coverage_rate=report.revenue_coverage_rate,
        duplicate_rate=report.duplicate_rate,
        refund_reconciliation_rate=report.refund_reconciliation_rate,
        confidence_grade=report.confidence_grade,
        blocking_issues=json.loads(report.blocking_issues_json),
        content_hash=report.content_hash,
    )


def _snapshot_response(snapshot, report) -> AnalyticalSnapshotResponse:
    return AnalyticalSnapshotResponse(
        id=snapshot.id,
        tenant_id=snapshot.tenant_id,
        connection_id=snapshot.connection_id,
        company_ids=json.loads(snapshot.company_ids_json),
        period_start=snapshot.period_start,
        period_end=snapshot.period_end,
        comparison_period_start=snapshot.comparison_period_start,
        comparison_period_end=snapshot.comparison_period_end,
        source_models=json.loads(snapshot.source_models_json),
        extraction_manifest=json.loads(snapshot.extraction_manifest_json),
        row_counts=json.loads(snapshot.row_counts_json),
        currency=snapshot.currency,
        source_hash=snapshot.source_hash,
        metric_definition_version=snapshot.metric_definition_version,
        status=snapshot.status,
        created_by=snapshot.created_by,
        created_at=snapshot.created_at.isoformat(),
        data_quality=_quality_response(report),
    )


def _analysis_response(row) -> MarginAnalysisResponse:
    return MarginAnalysisResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        snapshot_id=row.snapshot_id,
        status=row.status,
        metric_definition_version=row.metric_definition_version,
        current_metrics=json.loads(row.current_metrics_json),
        comparison_metrics=json.loads(row.comparison_metrics_json),
        margin_bridge=json.loads(row.margin_bridge_json),
        product_drivers=json.loads(row.product_drivers_json),
        customer_drivers=json.loads(row.customer_drivers_json),
        warnings=json.loads(row.warnings_json),
        tolerance=row.tolerance,
        content_hash=row.content_hash,
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
    )
