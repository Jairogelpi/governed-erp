from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ActionPlanStep:
    step_number: int
    title: str
    description: str
    endpoint_hint: str
    method_hint: str
    severity: str          # blocking | required | optional
    prereqs_met: bool
    blocker_reason: str | None = None
    requires_operator_click: bool = True
    executable: bool = False


def enforce_safety(steps: list[ActionPlanStep]) -> list[ActionPlanStep]:
    """Guarantee every step is advisory-only — idempotent, always safe to call."""
    for step in steps:
        step.requires_operator_click = True
        step.executable = False
    return steps


def safety_summary(steps: list[ActionPlanStep]) -> str:
    blocking = [s for s in steps if s.severity == "blocking" and not s.prereqs_met]
    if not blocking:
        return "No blocking prerequisites. Operator can proceed step by step."
    titles = "; ".join(s.title for s in blocking[:3])
    return f"{len(blocking)} blocking step(s) require operator action first: {titles}."
