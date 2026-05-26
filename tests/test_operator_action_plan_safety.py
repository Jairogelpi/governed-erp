"""Sprint 42 — Action plan safety layer tests."""
from __future__ import annotations

from erpguard.product.operator_action_plan_safety import ActionPlanStep, enforce_safety, safety_summary


def _make_step(n: int, severity: str = "required", prereqs_met: bool = True) -> ActionPlanStep:
    return ActionPlanStep(
        step_number=n,
        title=f"Step {n}",
        description="desc",
        endpoint_hint="GET /v1/foo",
        method_hint="GET",
        severity=severity,
        prereqs_met=prereqs_met,
    )


def test_enforce_safety_sets_requires_operator_click():
    steps = [_make_step(1)]
    steps[0].requires_operator_click = False
    enforce_safety(steps)
    assert steps[0].requires_operator_click is True


def test_enforce_safety_sets_executable_false():
    steps = [_make_step(1)]
    steps[0].executable = True
    enforce_safety(steps)
    assert steps[0].executable is False


def test_enforce_safety_is_idempotent():
    steps = [_make_step(i) for i in range(1, 5)]
    enforce_safety(enforce_safety(steps))
    for s in steps:
        assert s.requires_operator_click is True
        assert s.executable is False


def test_safety_summary_no_blockers():
    steps = [_make_step(1, "blocking", prereqs_met=True)]
    msg = safety_summary(steps)
    assert "No blocking" in msg


def test_safety_summary_with_blockers():
    steps = [_make_step(1, "blocking", prereqs_met=False)]
    msg = safety_summary(steps)
    assert "1 blocking" in msg
    assert "Step 1" in msg


def test_safety_summary_counts_correctly():
    steps = [_make_step(i, "blocking", prereqs_met=False) for i in range(1, 4)]
    msg = safety_summary(steps)
    assert "3 blocking" in msg
