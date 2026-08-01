from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.dependencies.identity import get_db, require_role
from apps.api.schemas.benchmark import BenchmarkReportResponse, BenchmarkRunCreateRequest, BenchmarkRunResponse
from erpguard.application.benchmark.service import BenchmarkRunNotFound, BenchmarkService, BenchmarkValidationError
from erpguard.domain.identity.auth import Principal

router = APIRouter(prefix="/v1/benchmarks", tags=["benchmarks"])


@router.post("/runs", response_model=BenchmarkRunResponse, status_code=201)
def create_benchmark_run(
    request: BenchmarkRunCreateRequest,
    db: Session = Depends(get_db),
    principal: Principal = Depends(require_role("operator")),
) -> BenchmarkRunResponse:
    try:
        row = BenchmarkService(db).create_run(
            tenant_id=principal.tenant_id, dataset_version=request.dataset_version,
            configurations=request.configurations, repeats=request.repeats,
            created_by=principal.user_id,
        )
    except BenchmarkValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _run_response(row)


@router.get("/runs/{run_id}", response_model=BenchmarkRunResponse)
def get_benchmark_run(
    run_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> BenchmarkRunResponse:
    try:
        row = BenchmarkService(db).get(tenant_id=principal.tenant_id, run_id=run_id)
    except BenchmarkRunNotFound as exc:
        raise HTTPException(status_code=404, detail="benchmark_run_not_found") from exc
    return _run_response(row)


@router.get("/runs/{run_id}/report", response_model=BenchmarkReportResponse)
def get_benchmark_report(
    run_id: str, db: Session = Depends(get_db), principal: Principal = Depends(require_role("viewer"))
) -> BenchmarkReportResponse:
    try:
        report = BenchmarkService(db).report(tenant_id=principal.tenant_id, run_id=run_id)
    except BenchmarkRunNotFound as exc:
        raise HTTPException(status_code=404, detail="benchmark_run_not_found") from exc
    return BenchmarkReportResponse(**report)


def _run_response(row) -> BenchmarkRunResponse:
    return BenchmarkRunResponse(
        id=row.id,
        tenant_id=row.tenant_id,
        dataset_version=row.dataset_version,
        dataset_manifest_hash=row.dataset_manifest_hash,
        configurations=json.loads(row.configurations_json),
        repeats=row.repeats,
        status=row.status,
        created_by=row.created_by,
        started_at=row.started_at.isoformat(),
        completed_at=row.completed_at.isoformat() if row.completed_at else None,
    )
