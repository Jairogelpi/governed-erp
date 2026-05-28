from __future__ import annotations

from fastapi import APIRouter, HTTPException

from apps.api.schemas.fake_erp_regression import (
    FakeERPRegressionAuditEntrySchema,
    FakeERPRegressionAuditResponse,
    FakeERPRegressionCaseRequest,
    FakeERPRegressionCaseResponse,
    FakeERPRegressionRunRequest,
    FakeERPRegressionRunResponse,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_regression_audit import get_fake_erp_regression_audit
from erpguard.product.fake_erp_regression_case import (
    FakeERPRegressionCaseCreateRequest,
    create_manual_fake_erp_regression_case,
    get_manual_fake_erp_regression_case,
)
from erpguard.product.fake_erp_regression_run import (
    FakeERPRegressionRunRequest as FakeERPRegressionRunServiceRequest,
    create_manual_fake_erp_regression_run,
    get_manual_fake_erp_regression_run,
)


router = APIRouter(prefix="/v1/operator-console/fake-erp-regression", tags=["fake-erp-regression"])


@router.post("/cases", response_model=FakeERPRegressionCaseResponse)
def create_regression_case(body: FakeERPRegressionCaseRequest):
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_fake_erp_regression_case(
            FakeERPRegressionCaseCreateRequest(
                version_id=body.version_id,
                dry_run_id=body.dry_run_id,
                name=body.name,
                execution_target=body.execution_target,
                inputs=body.inputs,
                expected_outcomes=body.expected_outcomes,
            ),
            db,
        )
        return FakeERPRegressionCaseResponse(**result.__dict__)
    finally:
        db.close()


@router.get("/cases/{case_id}", response_model=FakeERPRegressionCaseResponse)
def get_regression_case(case_id: str):
    init_db()
    db = SessionLocal()
    try:
        result = get_manual_fake_erp_regression_case(case_id=case_id, session=db)
        if result is None:
            raise HTTPException(status_code=404, detail="fake_erp_regression_case_not_found")
        return FakeERPRegressionCaseResponse(**result.__dict__)
    finally:
        db.close()


@router.post("/run", response_model=FakeERPRegressionRunResponse)
def run_regression_case(body: FakeERPRegressionRunRequest):
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_fake_erp_regression_run(
            FakeERPRegressionRunServiceRequest(
                case_id=body.case_id,
                token_id=body.token_id,
                actor=body.actor.model_dump(),
                reason=body.reason,
            ),
            db,
        )
        return FakeERPRegressionRunResponse(**result.__dict__)
    finally:
        db.close()


@router.get("/runs/{regression_run_id}", response_model=FakeERPRegressionRunResponse)
def get_regression_run(regression_run_id: str):
    init_db()
    db = SessionLocal()
    try:
        result = get_manual_fake_erp_regression_run(regression_run_id=regression_run_id, session=db)
        if result is None:
            raise HTTPException(status_code=404, detail="fake_erp_regression_run_not_found")
        return FakeERPRegressionRunResponse(**result.__dict__)
    finally:
        db.close()


@router.get("/audit", response_model=FakeERPRegressionAuditResponse)
def get_regression_audit(limit: int = 50):
    init_db()
    db = SessionLocal()
    try:
        result = get_fake_erp_regression_audit(session=db, limit=limit)
        return FakeERPRegressionAuditResponse(
            entries=[
                FakeERPRegressionAuditEntrySchema(
                    event_id=e.event_id,
                    regression_run_id=e.regression_run_id,
                    case_id=e.case_id,
                    version_id=e.version_id,
                    execution_id=e.execution_id,
                    evidence_pack_id=e.evidence_pack_id,
                    actor=e.actor,
                    event_type=e.event_type,
                    status=e.status,
                    detail=e.detail,
                    created_at=e.created_at,
                )
                for e in result.entries
            ],
            event_count=result.event_count,
        )
    finally:
        db.close()
