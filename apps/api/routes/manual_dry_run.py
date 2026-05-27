from __future__ import annotations

from fastapi import APIRouter, HTTPException
import json

from apps.api.schemas.manual_dry_run import (
    ManualDryRunRequest,
    ManualDryRunResponse,
    ManualDryRunAuditResponse,
    ManualDryRunAuditEntry,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.db.repositories import (
    get_active_skill_run,
    get_manual_dry_run_evidence_for_run,
)
from erpguard.product.manual_dry_run_audit import get_manual_dry_run_audit as get_manual_dry_run_audit_events
from erpguard.product.manual_dry_run_record import (
    ManualDryRunCreateRequest,
    create_manual_dry_run_record,
)


router = APIRouter(prefix="/v1/operator-console", tags=["manual-dry-run"])


@router.post("/action-plan/manual-dry-run", response_model=ManualDryRunResponse)
def create_manual_dry_run(body: ManualDryRunRequest):
    init_db()
    db = SessionLocal()
    try:
        result = create_manual_dry_run_record(
            ManualDryRunCreateRequest(
                version_id=body.version_id,
                token_id=body.token_id,
                actor=body.actor.model_dump(),
                source_plan_id=body.source_plan_id,
                source_step_number=body.source_step_number,
                mode=body.mode,
                inputs=body.inputs,
                reason=body.reason,
                requested_target=body.requested_target,
            ),
            db,
        )
        return ManualDryRunResponse(**result.__dict__)
    finally:
        db.close()


@router.get("/action-plan/manual-dry-run/{run_id}", response_model=ManualDryRunResponse)
def get_manual_dry_run(run_id: str):
    init_db()
    db = SessionLocal()
    try:
        run = get_active_skill_run(db, run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="run_not_found")
        summary = json.loads(run.summary_json or "{}") if run.summary_json else {}
        evidence = get_manual_dry_run_evidence_for_run(db, run_id)
        return ManualDryRunResponse(
            run_id=run.id,
            version_id=run.version_id,
            status=run.status,
            mode="dry_run",
            execution_performed=False,
            simulation_performed=True,
            erp_writes_performed=False,
            browser_control_performed=False,
            mcp_execution_performed=False,
            llm_runtime_used=False,
            scheduler_used=False,
            fake_erp_execution_performed=False,
            odoo_execution_performed=False,
            active_skill_run_created=True,
            evidence_id=(evidence.id if evidence is not None else None),
            audit_recorded=True,
            result_summary=summary.get("result_summary", "Manual dry-run record retrieved."),
            blocking_reasons=summary.get("blocking_reasons", []),
        )
    finally:
        db.close()


@router.get("/action-plan/manual-dry-run-audit", response_model=ManualDryRunAuditResponse)
def get_manual_dry_run_audit(limit: int = 50):
    init_db()
    db = SessionLocal()
    try:
        result = get_manual_dry_run_audit_events(session=db, limit=limit)
        return ManualDryRunAuditResponse(
            entries=[
                ManualDryRunAuditEntry(
                    event_id=e.event_id,
                    run_id=e.run_id,
                    version_id=e.version_id,
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
