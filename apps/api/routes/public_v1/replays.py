"""Historical replay API (master spec section 15.8 / Phase 12).

The create route is nested under /v1/processes/... per the spec, not under
this module's /v1/replays prefix, so it's declared on a second router with
no shared prefix and mounted alongside the replays router in __init__.py.
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.replays import (
    ReplayCaseResponse,
    ReplayComparisonResponse,
    ReplayCreateRequest,
    ReplayResponse,
)
from erpguard.domain.identity.auth import Principal
from erpguard.domain.replays.service import (
    ProcessDefinitionNotFound,
    ReplayNotFound,
    ReplayService,
    ReplayValidationError,
)

router = APIRouter(prefix="/v1/replays", tags=["replays"])
processes_router = APIRouter(prefix="/v1/processes", tags=["replays"])


@processes_router.post(
    "/{process_key}/versions/{version}/replays",
    response_model=ReplayResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_replay(
    process_key: str,
    version: str,
    request: ReplayCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> ReplayResponse:
    try:
        row = ReplayService(db).create_replay(
            tenant_id=principal.tenant_id,
            process_key=process_key,
            version=version,
            object_type=request.object_type,
        )
    except ProcessDefinitionNotFound as exc:
        raise HTTPException(status_code=404, detail="process_definition_not_found") from exc
    return _response(row)


@router.get("/{replay_id}", response_model=ReplayResponse)
def get_replay(
    replay_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ReplayResponse:
    try:
        return _response(ReplayService(db).get_replay(tenant_id=principal.tenant_id, replay_id=replay_id))
    except ReplayNotFound as exc:
        raise HTTPException(status_code=404, detail="replay_not_found") from exc


@router.get("/{replay_id}/cases", response_model=list[ReplayCaseResponse])
def list_replay_cases(
    replay_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> list[ReplayCaseResponse]:
    try:
        rows = ReplayService(db).list_cases(tenant_id=principal.tenant_id, replay_id=replay_id)
    except ReplayNotFound as exc:
        raise HTTPException(status_code=404, detail="replay_not_found") from exc
    return [_case_response(row) for row in rows]


@router.get("/{replay_id}/comparison", response_model=ReplayComparisonResponse)
def get_replay_comparison(
    replay_id: str,
    baseline_replay_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> ReplayComparisonResponse:
    try:
        result = ReplayService(db).compare(
            tenant_id=principal.tenant_id,
            baseline_replay_id=baseline_replay_id,
            candidate_replay_id=replay_id,
        )
    except ReplayNotFound as exc:
        raise HTTPException(status_code=404, detail="replay_not_found") from exc
    return ReplayComparisonResponse(**result)


@router.post("/{replay_id}/freeze", response_model=ReplayResponse)
def freeze_replay(
    replay_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> ReplayResponse:
    try:
        row = ReplayService(db).freeze(tenant_id=principal.tenant_id, replay_id=replay_id)
    except ReplayNotFound as exc:
        raise HTTPException(status_code=404, detail="replay_not_found") from exc
    except ReplayValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


def _response(row) -> ReplayResponse:
    return ReplayResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        process_key=row.process_key,
        version=row.version,
        object_type=row.object_type,
        status=row.status,
        policy_version=row.policy_version,
        connector_simulator_version=row.connector_simulator_version,
        case_count=row.case_count,
        created_at=row.created_at.isoformat(),
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
        frozen_at=row.frozen_at.isoformat() if row.frozen_at else None,
    )


def _case_response(row) -> ReplayCaseResponse:
    return ReplayCaseResponse(
        case_id=row.case_id,
        status=row.status,
        decision_trace=json.loads(row.decision_trace_json),
        predicted_effects=json.loads(row.predicted_effects_json),
        safety_violations=json.loads(row.safety_violations_json),
        regressions=json.loads(row.regressions_json),
        metrics=json.loads(row.metrics_json),
        deterministic_trace_hash=row.deterministic_trace_hash,
        declared_decision_count=row.declared_decision_count,
        evaluated_decision_count=row.evaluated_decision_count,
        unsupported_decisions=json.loads(row.unsupported_decisions_json),
        decision_coverage_rate=row.decision_coverage_rate,
    )
