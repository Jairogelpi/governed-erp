from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_skill_version_record


@dataclass(frozen=True)
class RunPlanStep:
    step_index: int
    step_id: str
    step_type: str
    description: str
    guard_check: str
    will_execute: bool = False
    estimated_impact: str = "none"


@dataclass(frozen=True)
class RunPlanResult:
    version_id: str
    skill_id: str
    plan_ready: bool
    step_count: int
    steps: list[RunPlanStep] = field(default_factory=list)
    guard_names: list[str] = field(default_factory=list)
    runtime_type: str = ""
    plan_is_dry_run: bool = True
    will_execute: bool = False
    can_execute: bool = False
    is_advisory_only: bool = True
    blocking_reason: str = ""


def build_run_plan(version_id: str, session) -> RunPlanResult:
    """Build a non-executing run plan from the active version's steps."""
    version_row = get_ui_skill_version_record(session, version_id)
    if version_row is None:
        return RunPlanResult(
            version_id=version_id,
            skill_id="",
            plan_ready=False,
            step_count=0,
            blocking_reason="version_not_found",
        )

    if not (version_row.status == "active" and version_row.is_active):
        return RunPlanResult(
            version_id=version_id,
            skill_id=version_row.skill_id,
            plan_ready=False,
            step_count=0,
            runtime_type=version_row.runtime_type,
            blocking_reason=f"Version is not active (status={version_row.status})",
        )

    raw_steps = json.loads(version_row.steps_json)
    guard_names = json.loads(version_row.guard_names_json)

    plan_steps: list[RunPlanStep] = []
    if raw_steps:
        for i, s in enumerate(raw_steps):
            plan_steps.append(RunPlanStep(
                step_index=i,
                step_id=s.get("id", f"step_{i}"),
                step_type=s.get("type", "unknown"),
                description=s.get("description", ""),
                guard_check="formula_guard" if guard_names else "none",
                will_execute=False,
                estimated_impact="none",
            ))
    else:
        plan_steps.append(RunPlanStep(
            step_index=0,
            step_id="advisory_step",
            step_type="advisory_read",
            description="Advisory skill — no concrete steps defined; execution would be a governed no-op",
            guard_check="agent_advisory_guard",
            will_execute=False,
            estimated_impact="none",
        ))

    return RunPlanResult(
        version_id=version_id,
        skill_id=version_row.skill_id,
        plan_ready=True,
        step_count=len(plan_steps),
        steps=plan_steps,
        guard_names=guard_names,
        runtime_type=version_row.runtime_type,
    )
