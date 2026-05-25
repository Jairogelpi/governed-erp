from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_agent_skill_run_preview_event,
    get_ui_skill_version_record,
)
from erpguard.product.agent_skill_execution_gate import ExecutionGateResult, evaluate_execution_gate
from erpguard.product.agent_skill_run_plan_builder import RunPlanResult, build_run_plan
from erpguard.product.agent_skill_run_preview_validator import (
    RunPreviewValidationResult,
    validate_run_preview_eligibility,
)


@dataclass(frozen=True)
class RunPreviewResult:
    version_id: str
    skill_id: str
    preview_ready: bool
    eligible: bool
    plan_ready: bool
    gate_passed: bool
    execution_ready: bool
    step_count: int
    runtime_type: str
    guard_names: list[str] = field(default_factory=list)
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def get_run_preview(version_id: str, session) -> RunPreviewResult:
    """Build and evaluate a manual run preview — plan-only, no execution."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return RunPreviewResult(
            version_id=version_id,
            skill_id="",
            preview_ready=False,
            eligible=False,
            plan_ready=False,
            gate_passed=False,
            execution_ready=False,
            step_count=0,
            runtime_type="",
            blocking_reason="version_not_found",
        )

    validation = validate_run_preview_eligibility(version_id, session)
    if not validation.eligible:
        return RunPreviewResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            preview_ready=False,
            eligible=False,
            plan_ready=False,
            gate_passed=False,
            execution_ready=False,
            step_count=0,
            runtime_type=version_row.runtime_type,
            blocking_reason="; ".join(validation.blocking_reasons),
        )

    plan = build_run_plan(version_id, session)
    gate = evaluate_execution_gate(version_id, session)

    preview_ready = plan.plan_ready and gate.gate_passed

    create_agent_skill_run_preview_event(
        session,
        version_id=version_id,
        skill_id=version_row.skill_id,
        step="run_preview_completed",
        status="ready" if preview_ready else "not_ready",
        detail_json=json.dumps({
            "eligible": validation.eligible,
            "plan_ready": plan.plan_ready,
            "gate_passed": gate.gate_passed,
            "execution_ready": gate.execution_ready,
            "step_count": plan.step_count,
            "will_execute": False,
        }),
    )

    return RunPreviewResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        preview_ready=preview_ready,
        eligible=validation.eligible,
        plan_ready=plan.plan_ready,
        gate_passed=gate.gate_passed,
        execution_ready=gate.execution_ready,
        step_count=plan.step_count,
        runtime_type=version_row.runtime_type,
        guard_names=plan.guard_names,
    )
