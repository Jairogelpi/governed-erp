from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException

from apps.api.schemas.fake_erp_execution import (
    FakeERPExecutionAuditEntrySchema,
    FakeERPExecutionAuditResponse,
    FakeERPExecutionRequest,
    FakeERPExecutionResponse,
)
from erpguard.db.repositories import get_fake_erp_execution_record
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.fake_erp_execution_audit import get_fake_erp_execution_audit
from erpguard.product.fake_erp_execution_record import (
    FakeERPExecutionCreateRequest,
    create_fake_erp_execution,
)


router = APIRouter(prefix="/v1/operator-console/action-plan", tags=["fake-erp-execution"])


@router.post("/fake-erp-execution", response_model=FakeERPExecutionResponse)
def run_fake_erp_execution(body: FakeERPExecutionRequest):
    init_db()
    db = SessionLocal()
    try:
        result = create_fake_erp_execution(
            FakeERPExecutionCreateRequest(
                version_id=body.version_id,
                dry_run_id=body.dry_run_id,
                token_id=body.token_id,
                actor=body.actor.model_dump(),
                execution_target=body.execution_target,
                inputs=body.inputs,
                reason=body.reason,
            ),
            db,
        )
        return FakeERPExecutionResponse(**result.__dict__)
    finally:
        db.close()


@router.get("/fake-erp-execution/{execution_id}", response_model=FakeERPExecutionResponse)
def get_fake_erp_execution(execution_id: str):
    init_db()
    db = SessionLocal()
    try:
        row = get_fake_erp_execution_record(db, execution_id)
        if row is None:
            raise HTTPException(status_code=404, detail="fake_erp_execution_not_found")
        safety = json.loads(row.safety_summary_json or "{}")
        return FakeERPExecutionResponse(
            execution_id=row.id,
            version_id=row.version_id,
            dry_run_id=row.dry_run_id,
            status=row.status,
            execution_target=row.execution_target,
            execution_performed=row.status == "completed",
            fake_erp_execution_performed=row.status == "completed",
            odoo_execution_performed=bool(safety.get("odoo_execution_performed", False)),
            real_erp_execution_performed=bool(safety.get("real_erp_execution_performed", False)),
            erp_writes_performed=bool(safety.get("erp_writes_performed", False)),
            browser_control_performed=bool(safety.get("browser_control_performed", False)),
            mcp_execution_performed=bool(safety.get("mcp_execution_performed", False)),
            llm_runtime_used=bool(safety.get("llm_runtime_used", False)),
            scheduler_used=bool(safety.get("scheduler_used", False)),
            external_http_performed=bool(safety.get("external_http_performed", False)),
            steps_executed=row.steps_executed,
            steps_blocked=row.steps_blocked,
            evidence_pack_id=row.evidence_pack_id,
            audit_recorded=True,
            result_summary=row.result_summary,
            blocking_reasons=[],
        )
    finally:
        db.close()


@router.get("/fake-erp-execution-audit", response_model=FakeERPExecutionAuditResponse)
def get_fake_erp_execution_audit_endpoint(limit: int = 50):
    init_db()
    db = SessionLocal()
    try:
        result = get_fake_erp_execution_audit(session=db, limit=limit)
        return FakeERPExecutionAuditResponse(
            entries=[
                FakeERPExecutionAuditEntrySchema(
                    event_id=e.event_id,
                    execution_id=e.execution_id,
                    version_id=e.version_id,
                    dry_run_id=e.dry_run_id,
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
