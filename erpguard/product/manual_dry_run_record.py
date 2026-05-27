from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from erpguard.db.repositories import (
    add_active_skill_run_event,
    create_active_skill_run,
    get_ui_skill_version_record,
    update_active_skill_run,
)
from erpguard.product.manual_dry_run_audit import persist_manual_dry_run_audit_event
from erpguard.product.manual_dry_run_evidence import persist_manual_dry_run_evidence
from erpguard.product.manual_dry_run_gate import ManualDryRunGateRequest, evaluate_manual_dry_run_gate


@dataclass(frozen=True)
class ManualDryRunCreateRequest:
    version_id: str
    token_id: str
    actor: dict
    source_plan_id: str | None = None
    source_step_number: int | None = None
    mode: str = "dry_run"
    inputs: dict = field(default_factory=dict)
    reason: str | None = None
    requested_target: str | None = None


@dataclass(frozen=True)
class ManualDryRunCreateResult:
    run_id: str
    version_id: str
    status: str
    mode: str
    execution_performed: bool
    simulation_performed: bool
    erp_writes_performed: bool
    browser_control_performed: bool
    mcp_execution_performed: bool
    llm_runtime_used: bool
    scheduler_used: bool
    active_skill_run_created: bool
    fake_erp_execution_performed: bool
    odoo_execution_performed: bool
    evidence_id: str | None
    audit_recorded: bool
    result_summary: str
    blocking_reasons: list[str]


def create_manual_dry_run_record(req: ManualDryRunCreateRequest, session) -> ManualDryRunCreateResult:
    actor_id = str((req.actor or {}).get("id") or "").strip()
    requested_target = (req.requested_target or "simulation").strip() or "simulation"

    gate = evaluate_manual_dry_run_gate(
        ManualDryRunGateRequest(
            version_id=req.version_id,
            token_id=req.token_id,
            mode=req.mode,
            actor_id=actor_id,
            requested_target=requested_target,
        ),
        session,
    )

    if not gate.passed:
        blocked_run_id = f"dryrun_{uuid4().hex[:16]}"
        persist_manual_dry_run_audit_event(
            run_id=blocked_run_id,
            version_id=req.version_id,
            actor=req.actor,
            event_type="requested",
            status="info",
            detail={
                "source_plan_id": req.source_plan_id,
                "source_step_number": req.source_step_number,
                "token_id": req.token_id,
                "requested_target": requested_target,
                "mode": req.mode,
            },
            session=session,
        )
        persist_manual_dry_run_audit_event(
            run_id=blocked_run_id,
            version_id=req.version_id,
            actor=req.actor,
            event_type="gate_blocked",
            status="blocked",
            detail={"checks": gate.checks, "blocking_reasons": gate.blocking_reasons},
            session=session,
        )
        persist_manual_dry_run_audit_event(
            run_id=blocked_run_id,
            version_id=req.version_id,
            actor=req.actor,
            event_type="blocked",
            status="blocked",
            detail={"blocking_reasons": gate.blocking_reasons},
            session=session,
        )
        return ManualDryRunCreateResult(
            run_id=blocked_run_id,
            version_id=req.version_id,
            status="blocked",
            mode="dry_run",
            execution_performed=False,
            simulation_performed=False,
            erp_writes_performed=False,
            browser_control_performed=False,
            mcp_execution_performed=False,
            llm_runtime_used=False,
            scheduler_used=False,
            active_skill_run_created=False,
            fake_erp_execution_performed=False,
            odoo_execution_performed=False,
            evidence_id=None,
            audit_recorded=True,
            result_summary="Manual dry-run gate blocked. No execution record was created.",
            blocking_reasons=gate.blocking_reasons,
        )

    version = get_ui_skill_version_record(session, req.version_id)
    if version is None:
        return ManualDryRunCreateResult(
            run_id=f"dryrun_{uuid4().hex[:16]}",
            version_id=req.version_id,
            status="blocked",
            mode="dry_run",
            execution_performed=False,
            simulation_performed=False,
            erp_writes_performed=False,
            browser_control_performed=False,
            mcp_execution_performed=False,
            llm_runtime_used=False,
            scheduler_used=False,
            active_skill_run_created=False,
            fake_erp_execution_performed=False,
            odoo_execution_performed=False,
            evidence_id=None,
            audit_recorded=True,
            result_summary="Version not found.",
            blocking_reasons=["version_not_found"],
        )

    run = create_active_skill_run(
        session,
        version_id=req.version_id,
        skill_id=version.skill_id,
        actor=actor_id,
        target_base_url="manual://dry-run",
        inputs_json=json.dumps(req.inputs),
        gate_result_json=json.dumps(
            {
                "checks": gate.checks,
                "blocking_reasons": gate.blocking_reasons,
                "token_id": req.token_id,
                "requested_target": requested_target,
            }
        ),
        input_validation_json=json.dumps({"mode": req.mode, "actor_present": bool(actor_id)}),
    )

    persist_manual_dry_run_audit_event(
        run_id=run.id,
        version_id=req.version_id,
        actor=req.actor,
        event_type="requested",
        status="info",
        detail={
            "source_plan_id": req.source_plan_id,
            "source_step_number": req.source_step_number,
            "token_id": req.token_id,
            "requested_target": requested_target,
            "mode": req.mode,
            "reason": req.reason,
        },
        session=session,
    )
    persist_manual_dry_run_audit_event(
        run_id=run.id,
        version_id=req.version_id,
        actor=req.actor,
        event_type="gate_passed",
        status="ok",
        detail={"checks": gate.checks},
        session=session,
    )

    add_active_skill_run_event(
        session,
        run_id=run.id,
        event_type="requested",
        status="info",
        detail="manual dry-run requested",
        payload_json=json.dumps({"source_plan_id": req.source_plan_id, "source_step_number": req.source_step_number}),
    )

    evidence = persist_manual_dry_run_evidence(
        run_id=run.id,
        version_id=req.version_id,
        skill_id=version.skill_id,
        actor=req.actor,
        mode="dry_run",
        inputs=req.inputs,
        preview_reference_id=gate.preview_reference_id,
        source_plan_id=req.source_plan_id,
        source_step_number=req.source_step_number,
        gate_result={"checks": gate.checks, "blocking_reasons": gate.blocking_reasons},
        steps_json=version.steps_json,
        session=session,
    )

    result_summary = "Manual dry-run record created. No ERP action was executed."
    update_active_skill_run(
        session,
        run.id,
        status="completed",
        summary_json=json.dumps({
            "result_summary": result_summary,
            "mode": "dry_run",
            "execution_performed": False,
            "simulation_performed": True,
            "evidence_id": evidence.evidence_id,
        }),
        finished_at=datetime.now(timezone.utc),
    )

    add_active_skill_run_event(
        session,
        run_id=run.id,
        event_type="dry_run_record_created",
        status="info",
        detail="dry-run record created",
        payload_json=json.dumps({"evidence_id": evidence.evidence_id}),
    )
    add_active_skill_run_event(
        session,
        run_id=run.id,
        event_type="completed",
        status="completed",
        detail="manual dry-run completed without execution",
        payload_json=json.dumps({"result_summary": result_summary}),
    )

    persist_manual_dry_run_audit_event(
        run_id=run.id,
        version_id=req.version_id,
        actor=req.actor,
        event_type="dry_run_record_created",
        status="completed",
        detail={"evidence_id": evidence.evidence_id},
        session=session,
    )
    persist_manual_dry_run_audit_event(
        run_id=run.id,
        version_id=req.version_id,
        actor=req.actor,
        event_type="completed",
        status="completed",
        detail={"result_summary": result_summary},
        session=session,
    )

    return ManualDryRunCreateResult(
        run_id=run.id,
        version_id=req.version_id,
        status="completed",
        mode="dry_run",
        execution_performed=False,
        simulation_performed=True,
        erp_writes_performed=False,
        browser_control_performed=False,
        mcp_execution_performed=False,
        llm_runtime_used=False,
        scheduler_used=False,
        active_skill_run_created=True,
        fake_erp_execution_performed=False,
        odoo_execution_performed=False,
        evidence_id=evidence.evidence_id,
        audit_recorded=True,
        result_summary=result_summary,
        blocking_reasons=[],
    )
