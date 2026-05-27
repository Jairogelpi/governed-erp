from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from erpguard.db.repositories import (
    create_fake_erp_execution_record,
    get_ui_skill_version_record,
    update_fake_erp_execution_record,
)
from erpguard.product.fake_erp_execution_audit import persist_fake_erp_execution_audit_event
from erpguard.product.fake_erp_execution_evidence import persist_fake_erp_execution_evidence
from erpguard.product.fake_erp_execution_gate import (
    FakeERPExecutionGateRequest,
    evaluate_fake_erp_execution_gate,
)
from erpguard.product.fake_erp_execution_runtime import run_controlled_fake_erp_runtime


@dataclass(frozen=True)
class FakeERPExecutionCreateRequest:
    version_id: str
    dry_run_id: str
    token_id: str
    actor: dict
    execution_target: str
    inputs: dict = field(default_factory=dict)
    reason: str | None = None


@dataclass(frozen=True)
class FakeERPExecutionCreateResult:
    execution_id: str
    version_id: str
    dry_run_id: str
    status: str
    execution_target: str
    execution_performed: bool
    fake_erp_execution_performed: bool
    odoo_execution_performed: bool
    real_erp_execution_performed: bool
    erp_writes_performed: bool
    browser_control_performed: bool
    mcp_execution_performed: bool
    llm_runtime_used: bool
    scheduler_used: bool
    external_http_performed: bool
    steps_executed: int
    steps_blocked: int
    evidence_pack_id: str | None
    audit_recorded: bool
    result_summary: str
    blocking_reasons: list[str]


def create_fake_erp_execution(req: FakeERPExecutionCreateRequest, session) -> FakeERPExecutionCreateResult:
    actor_id = str((req.actor or {}).get("id") or "").strip()
    execution_id = f"fexec_{uuid4().hex[:16]}"
    gate = evaluate_fake_erp_execution_gate(
        FakeERPExecutionGateRequest(
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            token_id=req.token_id,
            actor_id=actor_id,
            execution_target=req.execution_target,
        ),
        session,
    )

    if not gate.passed:
        persist_fake_erp_execution_audit_event(
            execution_id=execution_id,
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            actor=req.actor,
            event_type="requested",
            status="info",
            detail={"token_id": req.token_id, "execution_target": req.execution_target, "reason": req.reason},
            session=session,
        )
        persist_fake_erp_execution_audit_event(
            execution_id=execution_id,
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            actor=req.actor,
            event_type="gate_blocked",
            status="blocked",
            detail={"checks": gate.checks, "blocking_reasons": gate.blocking_reasons},
            session=session,
        )
        persist_fake_erp_execution_audit_event(
            execution_id=execution_id,
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            actor=req.actor,
            event_type="execution_blocked",
            status="blocked",
            detail={"blocking_reasons": gate.blocking_reasons},
            session=session,
        )
        return FakeERPExecutionCreateResult(
            execution_id=execution_id,
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            status="blocked",
            execution_target=req.execution_target,
            execution_performed=False,
            fake_erp_execution_performed=False,
            odoo_execution_performed=False,
            real_erp_execution_performed=False,
            erp_writes_performed=False,
            browser_control_performed=False,
            mcp_execution_performed=False,
            llm_runtime_used=False,
            scheduler_used=False,
            external_http_performed=False,
            steps_executed=0,
            steps_blocked=0,
            evidence_pack_id=None,
            audit_recorded=True,
            result_summary="Controlled Fake ERP execution blocked. No real ERP was touched.",
            blocking_reasons=gate.blocking_reasons,
        )

    version = get_ui_skill_version_record(session, req.version_id)
    if version is None:
        raise ValueError("version_not_found")

    create_fake_erp_execution_record(
        session,
        execution_id=execution_id,
        version_id=req.version_id,
        skill_id=version.skill_id,
        dry_run_id=req.dry_run_id,
        actor_json=json.dumps(req.actor),
        execution_target="fake_erp",
        inputs_json=json.dumps(req.inputs),
        status="running",
        step_count=0,
        steps_executed=0,
        steps_blocked=0,
        result_summary="Controlled Fake ERP execution started.",
        safety_summary_json=json.dumps({}),
    )

    persist_fake_erp_execution_audit_event(
        execution_id=execution_id,
        version_id=req.version_id,
        dry_run_id=req.dry_run_id,
        actor=req.actor,
        event_type="requested",
        status="info",
        detail={"token_id": req.token_id, "execution_target": req.execution_target, "reason": req.reason},
        session=session,
    )
    persist_fake_erp_execution_audit_event(
        execution_id=execution_id,
        version_id=req.version_id,
        dry_run_id=req.dry_run_id,
        actor=req.actor,
        event_type="gate_passed",
        status="ok",
        detail={"checks": gate.checks},
        session=session,
    )
    persist_fake_erp_execution_audit_event(
        execution_id=execution_id,
        version_id=req.version_id,
        dry_run_id=req.dry_run_id,
        actor=req.actor,
        event_type="execution_started",
        status="running",
        detail={"allowlisted_steps": gate.allowlisted_steps},
        session=session,
    )

    runtime = run_controlled_fake_erp_runtime(allowlisted_steps=gate.allowlisted_steps, inputs=req.inputs)

    for step in runtime.steps:
        step_detail = {
            "step_number": step.step_number,
            "step_name": step.step_name,
            "operation": step.operation,
            "input_snapshot": step.input_snapshot,
        }
        persist_fake_erp_execution_audit_event(
            execution_id=execution_id,
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            actor=req.actor,
            event_type="step_started",
            status="running",
            detail=step_detail,
            session=session,
        )
        persist_fake_erp_execution_audit_event(
            execution_id=execution_id,
            version_id=req.version_id,
            dry_run_id=req.dry_run_id,
            actor=req.actor,
            event_type="step_completed",
            status=step.status,
            detail={**step_detail, "actual_fake_effect": step.actual_fake_effect},
            session=session,
        )

    evidence = persist_fake_erp_execution_evidence(
        execution_id=execution_id,
        version_id=req.version_id,
        skill_id=version.skill_id,
        dry_run_id=req.dry_run_id,
        actor=req.actor,
        execution_target="fake_erp",
        inputs=req.inputs,
        steps=[step.__dict__ for step in runtime.steps],
        session=session,
    )
    safety_summary = {
        "real_erp_execution_performed": False,
        "odoo_execution_performed": False,
        "erp_writes_performed": False,
        "browser_control_performed": False,
        "mcp_execution_performed": False,
        "llm_runtime_used": False,
        "scheduler_used": False,
        "external_http_performed": False,
    }
    update_fake_erp_execution_record(
        session,
        execution_id,
        status="completed",
        step_count=runtime.step_count,
        steps_executed=runtime.steps_executed,
        steps_blocked=runtime.steps_blocked,
        result_summary=runtime.result_summary,
        safety_summary_json=json.dumps(safety_summary),
        evidence_pack_id=evidence.evidence_pack_id,
        finished_at=datetime.now(timezone.utc),
    )
    persist_fake_erp_execution_audit_event(
        execution_id=execution_id,
        version_id=req.version_id,
        dry_run_id=req.dry_run_id,
        actor=req.actor,
        event_type="execution_completed",
        status="completed",
        detail={"steps_executed": runtime.steps_executed, "evidence_pack_id": evidence.evidence_pack_id},
        session=session,
    )

    return FakeERPExecutionCreateResult(
        execution_id=execution_id,
        version_id=req.version_id,
        dry_run_id=req.dry_run_id,
        status="completed",
        execution_target="fake_erp",
        execution_performed=True,
        fake_erp_execution_performed=True,
        odoo_execution_performed=False,
        real_erp_execution_performed=False,
        erp_writes_performed=False,
        browser_control_performed=False,
        mcp_execution_performed=False,
        llm_runtime_used=False,
        scheduler_used=False,
        external_http_performed=False,
        steps_executed=runtime.steps_executed,
        steps_blocked=runtime.steps_blocked,
        evidence_pack_id=evidence.evidence_pack_id,
        audit_recorded=True,
        result_summary=runtime.result_summary,
        blocking_reasons=[],
    )
