from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_agent_skill_run_preview_event,
    get_agent_candidate_activation_request_by_version,
    get_latest_agent_candidate_decision,
    get_ui_skill_version_record,
)


@dataclass(frozen=True)
class ExecutionGateCheck:
    check: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ExecutionGateResult:
    version_id: str
    skill_id: str
    gate_passed: bool
    execution_ready: bool
    checks: list[ExecutionGateCheck] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    will_execute: bool = False  # always False — preview only
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def evaluate_execution_gate(version_id: str, session) -> ExecutionGateResult:
    """Evaluate execution readiness — reads only, never executes."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return ExecutionGateResult(
            version_id=version_id,
            skill_id="",
            gate_passed=False,
            execution_ready=False,
            blocking_reasons=["Version not found"],
            blocking_reason="version_not_found",
        )

    latest_decision = get_latest_agent_candidate_decision(session, version_id)
    activation_req = get_agent_candidate_activation_request_by_version(session, version_id)

    checks: list[ExecutionGateCheck] = []
    blocking_reasons: list[str] = []

    is_active = version_row.status == "active" and version_row.is_active
    checks.append(ExecutionGateCheck(
        check="version_is_active",
        passed=is_active,
        detail=f"status={version_row.status}, is_active={version_row.is_active}",
    ))
    if not is_active:
        blocking_reasons.append(
            f"Version is not active (status={version_row.status})"
        )

    has_approve = (
        latest_decision is not None and latest_decision.decision == "approve"
    )
    checks.append(ExecutionGateCheck(
        check="approved_decision_on_record",
        passed=has_approve,
        detail=f"latest_decision={latest_decision.decision if latest_decision else 'none'}",
    ))
    if not has_approve:
        blocking_reasons.append("No approved decision on record")

    has_request = activation_req is not None
    checks.append(ExecutionGateCheck(
        check="activation_request_on_record",
        passed=has_request,
        detail=f"request_id={activation_req.id if activation_req else 'none'}",
    ))
    if not has_request:
        blocking_reasons.append("No explicit activation request on record")

    runtime_safe = version_row.runtime_type in ("agent_advisory", "deterministic_ui")
    checks.append(ExecutionGateCheck(
        check="runtime_type_safe",
        passed=runtime_safe,
        detail=f"runtime_type={version_row.runtime_type}",
    ))
    if not runtime_safe:
        blocking_reasons.append(
            f"runtime_type '{version_row.runtime_type}' not in approved list"
        )

    no_erp_writes = version_row.runtime_type == "agent_advisory"
    checks.append(ExecutionGateCheck(
        check="no_real_erp_writes",
        passed=no_erp_writes,
        detail="agent_advisory runtime never performs real ERP writes",
    ))
    if not no_erp_writes:
        blocking_reasons.append(
            "Runtime type may allow ERP writes — requires additional write-pilot approval"
        )

    # This gate returns execution_ready but never actually executes
    checks.append(ExecutionGateCheck(
        check="preview_does_not_execute",
        passed=True,
        detail="Execution gate evaluates readiness only — no run is created",
    ))

    gate_passed = len(blocking_reasons) == 0

    create_agent_skill_run_preview_event(
        session,
        version_id=version_id,
        skill_id=version_row.skill_id,
        step="execution_gate_evaluated",
        status="passed" if gate_passed else "failed",
        detail_json=json.dumps({
            "gate_passed": gate_passed,
            "execution_ready": gate_passed,
            "will_execute": False,
            "check_count": len(checks),
            "blocking_reasons": blocking_reasons,
        }),
    )

    return ExecutionGateResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        gate_passed=gate_passed,
        execution_ready=gate_passed,
        checks=checks,
        blocking_reasons=blocking_reasons,
    )
