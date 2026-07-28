from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4

from erpguard.db.repositories import (
    create_fake_erp_regression_run,
    get_fake_erp_regression_case,
    get_fake_erp_regression_run,
    update_fake_erp_regression_run,
)
from erpguard.product.fake_erp_evidence_pack import create_persisted_fake_erp_evidence_pack
from erpguard.product.fake_erp_execution_record import FakeERPExecutionCreateRequest, create_fake_erp_execution
from erpguard.product.fake_erp_regression_audit import persist_fake_erp_regression_audit_event


@dataclass(frozen=True)
class FakeERPRegressionRunRequest:
    case_id: str
    token_id: str
    actor: dict
    reason: str | None = None


@dataclass(frozen=True)
class FakeERPRegressionRunResult:
    regression_run_id: str
    case_id: str
    version_id: str
    dry_run_id: str
    execution_id: str | None
    evidence_pack_id: str | None
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
    comparison_summary: dict
    matched: bool
    audit_recorded: bool
    result_summary: str
    blocking_reasons: list[str]


def _compare_expected(expected: dict, pack_result, execution_result) -> dict:
    step_statuses = [str(step.get("status") or "") for step in pack_result.steps_snapshot]
    actual = {
        "status": execution_result.status,
        "steps_executed": execution_result.steps_executed,
        "steps_blocked": execution_result.steps_blocked,
        "result_summary": execution_result.result_summary,
        "execution_target": execution_result.execution_target,
        "step_statuses": step_statuses,
        "safety_summary": pack_result.safety_summary,
    }
    checks = []
    matched = True
    for key, expected_value in (expected or {}).items():
        actual_value = actual.get(key)
        ok = actual_value == expected_value
        if not ok:
            matched = False
        checks.append({"field": key, "expected": expected_value, "actual": actual_value, "matched": ok})
    return {"matched": matched, "checks": checks, "actual": actual}


def create_manual_fake_erp_regression_run(req: FakeERPRegressionRunRequest, session) -> FakeERPRegressionRunResult:
    actor = req.actor or {}
    actor_id = str(actor.get("id") or "").strip()
    run_id = f"fregrun_{uuid4().hex[:16]}"
    case = get_fake_erp_regression_case(session, req.case_id)
    if case is None:
        persist_fake_erp_regression_audit_event(
            regression_run_id=run_id,
            case_id=req.case_id,
            version_id="",
            execution_id=None,
            evidence_pack_id=None,
            actor=actor,
            event_type="requested",
            status="info",
            detail={"reason": req.reason},
            session=session,
        )
        persist_fake_erp_regression_audit_event(
            regression_run_id=run_id,
            case_id=req.case_id,
            version_id="",
            execution_id=None,
            evidence_pack_id=None,
            actor=actor,
            event_type="regression_blocked",
            status="blocked",
            detail={"blocking_reasons": ["case_not_found"]},
            session=session,
        )
        return FakeERPRegressionRunResult(
            regression_run_id=run_id,
            case_id=req.case_id,
            version_id="",
            dry_run_id="",
            execution_id=None,
            evidence_pack_id=None,
            status="blocked",
            execution_target="fake_erp",
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
            comparison_summary={},
            matched=False,
            audit_recorded=True,
            result_summary="Manual Fake ERP regression blocked. No Fake ERP execution was started.",
            blocking_reasons=["case_not_found"],
        )
    if not actor_id:
        persist_fake_erp_regression_audit_event(
            regression_run_id=run_id,
            case_id=case.id,
            version_id=case.version_id,
            execution_id=None,
            evidence_pack_id=None,
            actor=actor,
            event_type="requested",
            status="info",
            detail={"reason": req.reason},
            session=session,
        )
        persist_fake_erp_regression_audit_event(
            regression_run_id=run_id,
            case_id=case.id,
            version_id=case.version_id,
            execution_id=None,
            evidence_pack_id=None,
            actor=actor,
            event_type="regression_blocked",
            status="blocked",
            detail={"blocking_reasons": ["actor_required"]},
            session=session,
        )
        return FakeERPRegressionRunResult(
            regression_run_id=run_id,
            case_id=case.id,
            version_id=case.version_id,
            dry_run_id=case.dry_run_id,
            execution_id=None,
            evidence_pack_id=None,
            status="blocked",
            execution_target=case.execution_target,
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
            comparison_summary={},
            matched=False,
            audit_recorded=True,
            result_summary="Manual Fake ERP regression blocked. No Fake ERP execution was started.",
            blocking_reasons=["actor_required"],
        )

    inputs = json.loads(case.inputs_json or "{}")
    expected = json.loads(case.expected_outcomes_json or "{}")
    create_fake_erp_regression_run(
        session,
        regression_run_id=run_id,
        case_id=case.id,
        version_id=case.version_id,
        dry_run_id=case.dry_run_id,
        actor_json=json.dumps(actor),
        inputs_json=json.dumps(inputs),
        execution_target=case.execution_target,
        status="running",
        comparison_summary_json=json.dumps({}),
        result_summary="Manual Fake ERP regression started.",
        safety_summary_json=json.dumps({}),
    )
    persist_fake_erp_regression_audit_event(
        regression_run_id=run_id,
        case_id=case.id,
        version_id=case.version_id,
        execution_id=None,
        evidence_pack_id=None,
        actor=actor,
        event_type="requested",
        status="info",
        detail={"reason": req.reason},
        session=session,
    )

    execution = create_fake_erp_execution(
        FakeERPExecutionCreateRequest(
            version_id=case.version_id,
            dry_run_id=case.dry_run_id,
            token_id=req.token_id,
            actor=actor,
            execution_target="fake_erp",
            inputs=inputs,
            reason=req.reason,
        ),
        session,
    )
    if execution.status != "completed":
        persist_fake_erp_regression_audit_event(
            regression_run_id=run_id,
            case_id=case.id,
            version_id=case.version_id,
            execution_id=execution.execution_id,
            evidence_pack_id=None,
            actor=actor,
            event_type="execution_blocked",
            status="blocked",
            detail={"blocking_reasons": execution.blocking_reasons},
            session=session,
        )
        update_fake_erp_regression_run(
            session,
            run_id,
            execution_id=execution.execution_id,
            status="blocked",
            comparison_summary_json=json.dumps({}),
            result_summary="Manual Fake ERP regression blocked during controlled Fake ERP execution.",
            safety_summary_json=json.dumps(
                {
                    "odoo_execution_performed": False,
                    "real_erp_execution_performed": False,
                    "erp_writes_performed": False,
                    "browser_control_performed": False,
                    "mcp_execution_performed": False,
                    "llm_runtime_used": False,
                    "scheduler_used": False,
                    "external_http_performed": False,
                }
            ),
            finished_at=datetime.now(timezone.utc),
        )
        return FakeERPRegressionRunResult(
            regression_run_id=run_id,
            case_id=case.id,
            version_id=case.version_id,
            dry_run_id=case.dry_run_id,
            execution_id=execution.execution_id,
            evidence_pack_id=None,
            status="blocked",
            execution_target="fake_erp",
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
            comparison_summary={},
            matched=False,
            audit_recorded=True,
            result_summary="Manual Fake ERP regression blocked during controlled Fake ERP execution.",
            blocking_reasons=execution.blocking_reasons,
        )

    persist_fake_erp_regression_audit_event(
        regression_run_id=run_id,
        case_id=case.id,
        version_id=case.version_id,
        execution_id=execution.execution_id,
        evidence_pack_id=None,
        actor=actor,
        event_type="execution_completed",
        status="completed",
        detail={"execution_id": execution.execution_id},
        session=session,
    )
    pack = create_persisted_fake_erp_evidence_pack(execution_id=execution.execution_id, session=session)
    comparison = _compare_expected(expected, pack, execution)
    matched = bool(comparison.get("matched", False))
    result_summary = (
        "Manual Fake ERP regression matched expected outcomes."
        if matched
        else "Manual Fake ERP regression detected expected-vs-actual differences."
    )
    persist_fake_erp_regression_audit_event(
        regression_run_id=run_id,
        case_id=case.id,
        version_id=case.version_id,
        execution_id=execution.execution_id,
        evidence_pack_id=pack.pack_id,
        actor=actor,
        event_type="comparison_completed",
        status="completed" if matched else "mismatch",
        detail=comparison,
        session=session,
    )
    safety_summary = pack.safety_summary or {}
    update_fake_erp_regression_run(
        session,
        run_id,
        execution_id=execution.execution_id,
        evidence_pack_id=pack.pack_id,
        status="completed" if matched else "mismatch",
        comparison_summary_json=json.dumps(comparison),
        result_summary=result_summary,
        safety_summary_json=json.dumps(safety_summary),
        finished_at=datetime.now(timezone.utc),
    )
    persist_fake_erp_regression_audit_event(
        regression_run_id=run_id,
        case_id=case.id,
        version_id=case.version_id,
        execution_id=execution.execution_id,
        evidence_pack_id=pack.pack_id,
        actor=actor,
        event_type="regression_completed",
        status="completed" if matched else "mismatch",
        detail={"matched": matched},
        session=session,
    )
    return FakeERPRegressionRunResult(
        regression_run_id=run_id,
        case_id=case.id,
        version_id=case.version_id,
        dry_run_id=case.dry_run_id,
        execution_id=execution.execution_id,
        evidence_pack_id=pack.pack_id,
        status="completed" if matched else "mismatch",
        execution_target="fake_erp",
        execution_performed=True,
        fake_erp_execution_performed=True,
        odoo_execution_performed=bool(safety_summary.get("odoo_execution_performed", False)),
        real_erp_execution_performed=bool(safety_summary.get("real_erp_execution_performed", False)),
        erp_writes_performed=bool(safety_summary.get("erp_writes_performed", False)),
        browser_control_performed=bool(safety_summary.get("browser_control_performed", False)),
        mcp_execution_performed=bool(safety_summary.get("mcp_execution_performed", False)),
        llm_runtime_used=bool(safety_summary.get("llm_runtime_used", False)),
        scheduler_used=bool(safety_summary.get("scheduler_used", False)),
        external_http_performed=bool(safety_summary.get("external_http_performed", False)),
        comparison_summary=comparison,
        matched=matched,
        audit_recorded=True,
        result_summary=result_summary,
        blocking_reasons=[],
    )


def get_manual_fake_erp_regression_run(*, regression_run_id: str, session) -> FakeERPRegressionRunResult | None:
    row = get_fake_erp_regression_run(session, regression_run_id)
    if row is None:
        return None
    safety = json.loads(row.safety_summary_json or "{}")
    comparison = json.loads(row.comparison_summary_json or "{}")
    return FakeERPRegressionRunResult(
        regression_run_id=row.id,
        case_id=row.case_id,
        version_id=row.version_id,
        dry_run_id=row.dry_run_id,
        execution_id=row.execution_id,
        evidence_pack_id=row.evidence_pack_id,
        status=row.status,
        execution_target=row.execution_target,
        execution_performed=row.status in {"completed", "mismatch"},
        fake_erp_execution_performed=row.status in {"completed", "mismatch"},
        odoo_execution_performed=bool(safety.get("odoo_execution_performed", False)),
        real_erp_execution_performed=bool(safety.get("real_erp_execution_performed", False)),
        erp_writes_performed=bool(safety.get("erp_writes_performed", False)),
        browser_control_performed=bool(safety.get("browser_control_performed", False)),
        mcp_execution_performed=bool(safety.get("mcp_execution_performed", False)),
        llm_runtime_used=bool(safety.get("llm_runtime_used", False)),
        scheduler_used=bool(safety.get("scheduler_used", False)),
        external_http_performed=bool(safety.get("external_http_performed", False)),
        comparison_summary=comparison,
        matched=bool(comparison.get("matched", False)),
        audit_recorded=True,
        result_summary=row.result_summary,
        blocking_reasons=[],
    )
