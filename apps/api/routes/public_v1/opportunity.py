from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.opportunity import (
    MarginOpportunityGenerateRequest,
    MarginOpportunityListResponse,
    MarginOpportunityResponse,
)
from erpguard.application.decision_intelligence.analysis_service import (
    DecisionIntelligenceNotFound,
    DecisionIntelligenceService,
)
from erpguard.application.opportunity.service import OpportunityEngineService, OpportunityNotFound
from erpguard.domain.identity.auth import Principal


router = APIRouter(prefix="/v1/margin-analyses", tags=["opportunity"])


@router.post(
    "/{margin_analysis_id}/opportunities",
    response_model=MarginOpportunityListResponse,
    status_code=status.HTTP_201_CREATED,
)
def generate_margin_opportunities(
    margin_analysis_id: str,
    request: MarginOpportunityGenerateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> MarginOpportunityListResponse:
    try:
        analysis = DecisionIntelligenceService(db).get_analysis(
            tenant_id=principal.tenant_id, analysis_id=margin_analysis_id
        )
        rows = OpportunityEngineService(db).generate(
            tenant_id=principal.tenant_id,
            margin_analysis_id=margin_analysis_id,
            created_by=principal.user_id,
        )
    except (DecisionIntelligenceNotFound, OpportunityNotFound) as exc:
        raise HTTPException(status_code=404, detail="margin_analysis_not_found") from exc
    return MarginOpportunityListResponse(
        margin_analysis_id=margin_analysis_id,
        blocked=analysis.status == "blocked",
        opportunities=[_response(row) for row in rows],
    )


@router.get(
    "/{margin_analysis_id}/opportunities",
    response_model=MarginOpportunityListResponse,
)
def list_margin_opportunities(
    margin_analysis_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> MarginOpportunityListResponse:
    try:
        analysis = DecisionIntelligenceService(db).get_analysis(
            tenant_id=principal.tenant_id, analysis_id=margin_analysis_id
        )
    except DecisionIntelligenceNotFound as exc:
        raise HTTPException(status_code=404, detail="margin_analysis_not_found") from exc
    rows = OpportunityEngineService(db).list_opportunities(
        tenant_id=principal.tenant_id, margin_analysis_id=margin_analysis_id
    )
    return MarginOpportunityListResponse(
        margin_analysis_id=margin_analysis_id,
        blocked=analysis.status == "blocked",
        opportunities=[_response(row) for row in rows],
    )


def _response(row) -> MarginOpportunityResponse:
    return MarginOpportunityResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        margin_analysis_id=row.margin_analysis_id,
        snapshot_id=row.snapshot_id,
        cause=row.cause,
        affected_population=json.loads(row.affected_population_json),
        evidence=json.loads(row.evidence_json),
        impact_conservative=row.impact_conservative,
        impact_base=row.impact_base,
        impact_optimistic=row.impact_optimistic,
        confidence_band=row.confidence_band,
        risk_level=row.risk_level,
        implementation_cost=row.implementation_cost,
        payback_period_days=row.payback_period_days,
        proposed_action=row.proposed_action,
        status=row.status,
        content_hash=row.content_hash,
        created_by=row.created_by,
        created_at=row.created_at.isoformat(),
    )
