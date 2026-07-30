"""Execution Permit runtime API (master spec section 19 / 23.7, Phase 15).

Spec 23.7 "Runs" is the real, explicit path family this phase maps onto:
POST /v1/runs/plan, GET /v1/runs/{run_id}, POST /v1/runs/{run_id}/approve,
POST /v1/runs/{run_id}/execute. Two additions beyond the spec's literal
list, needed for the exit criteria ("revoked permits fail" needs something
to revoke) and to toggle the tenant kill switch this phase introduces --
POST /v1/runs/{run_id}/revoke and POST /v1/runs/kill-switch -- documented
here rather than silently invented. `GET .../evidence` and
`POST .../compensate` (spec 23.7) are out of scope for this phase (no live
Evidence Pack / compensation-planning logic exists yet).
"""

from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.execution_permits import (
    KillSwitchRequest,
    KillSwitchResponse,
    RunApproveRequest,
    RunPlanRequest,
    RunResponse,
)
from erpguard.domain.execution.kill_switch_service import KillSwitchService
from erpguard.domain.execution.permit_service import (
    PermitService,
    RunNotFound,
    RunValidationError,
    RunVerificationError,
)
from erpguard.domain.identity.auth import Principal

router = APIRouter(prefix="/v1/runs", tags=["executions"])


@router.post("/plan", response_model=RunResponse, status_code=status.HTTP_201_CREATED)
def plan_run(
    request: RunPlanRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> RunResponse:
    try:
        row = PermitService(db).plan(
            tenant_id=principal.tenant_id,
            actor_id=principal.user_id,
            connection_id=request.connection_id,
            skill_package_id=request.skill_package_id,
            capability=request.capability,
            idempotency_key=request.idempotency_key,
            capability_payload=request.capability_payload,
        )
    except RunValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.get("/{run_id}", response_model=RunResponse)
def get_run(
    run_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("viewer")),
) -> RunResponse:
    try:
        row = PermitService(db).get(tenant_id=principal.tenant_id, run_id=run_id)
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail="run_not_found") from exc
    return _response(row)


@router.post("/{run_id}/approve", response_model=RunResponse)
def approve_run(
    run_id: str,
    request: RunApproveRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> RunResponse:
    try:
        row = PermitService(db).approve(
            tenant_id=principal.tenant_id,
            run_id=run_id,
            approval_ids=request.approval_ids,
            ttl_seconds=request.ttl_seconds,
        )
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail="run_not_found") from exc
    except RunValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.post("/{run_id}/execute", response_model=RunResponse)
def execute_run(
    run_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> RunResponse:
    try:
        row = PermitService(db).execute(tenant_id=principal.tenant_id, run_id=run_id)
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail="run_not_found") from exc
    except RunVerificationError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except RunValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.post("/{run_id}/revoke", response_model=RunResponse)
def revoke_run(
    run_id: str,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> RunResponse:
    try:
        row = PermitService(db).revoke(tenant_id=principal.tenant_id, run_id=run_id)
    except RunNotFound as exc:
        raise HTTPException(status_code=404, detail="run_not_found") from exc
    except RunValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _response(row)


@router.post("/kill-switch", response_model=KillSwitchResponse)
def set_kill_switch(
    request: KillSwitchRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("admin")),
) -> KillSwitchResponse:
    row = KillSwitchService(db).set(tenant_id=principal.tenant_id, active=request.active)
    return KillSwitchResponse(tenant_id=row.tenant_id, active=row.active, updated_at=row.updated_at.isoformat())


def _response(row) -> RunResponse:
    return RunResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        actor_id=row.actor_id,
        connection_id=row.connection_id,
        connector_id=row.connector_id,
        skill_package_id=row.skill_package_id,
        process_version_id=row.process_version_id,
        skill_version_id=row.skill_version_id,
        capability=row.capability,
        operation_hash=row.operation_hash,
        native_plan_hash=row.native_plan_hash,
        state_snapshot_hash=row.state_snapshot_hash,
        capability_allowlist=json.loads(row.capability_allowlist_json or "[]"),
        approval_ids=json.loads(row.approval_ids_json or "[]"),
        idempotency_key=row.idempotency_key,
        status=row.status,
        created_at=row.created_at.isoformat(),
        approved_at=row.approved_at.isoformat() if row.approved_at else None,
        expires_at=row.expires_at.isoformat() if row.expires_at else None,
        executed_at=row.executed_at.isoformat() if row.executed_at else None,
        revoked_at=row.revoked_at.isoformat() if row.revoked_at else None,
        verification_result=json.loads(row.verification_result_json) if row.verification_result_json else None,
    )
