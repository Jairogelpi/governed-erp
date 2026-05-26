"""Sprint 42 — Action plan builder tests."""
from __future__ import annotations

import pytest

from erpguard.product.operator_action_plan_builder import build_action_plan
from erpguard.product.operator_action_plan_intent import classify_plan_intent
from erpguard.product.operator_action_plan_prerequisites import PrerequisiteState


def _build(goal: str, version_id: str | None = None, **pre_kwargs) -> object:
    intent = classify_plan_intent(goal)
    pre = PrerequisiteState(**pre_kwargs)
    return build_action_plan(intent, goal, pre, version_id)


@pytest.mark.parametrize("goal,expected_type", [
    ("preparar para preview", "prepare_for_run"),
    ("activar candidato", "activate_candidate"),
    ("fix governance gaps", "fix_governance_gaps"),
    ("encontrar reutilizable", "find_reusable_skill"),
    ("inspeccionar ciclo completo", "inspect_lifecycle"),
    ("asdfghjkl", "unknown"),
])
def test_plan_type_matches_intent(goal, expected_type):
    plan = _build(goal)
    assert plan.plan_type == expected_type


def test_plan_id_has_aplan_prefix():
    plan = _build("preparar para preview")
    assert plan.plan_id.startswith("aplan_")


def test_plan_has_steps():
    plan = _build("preparar para preview")
    assert plan.total_steps >= 1
    assert len(plan.steps) == plan.total_steps


def test_all_steps_advisory_only():
    plan = _build("activar candidato")
    for step in plan.steps:
        assert step.requires_operator_click is True
        assert step.executable is False


def test_will_execute_false():
    plan = _build("fix governance gaps")
    assert plan.will_execute is False
    assert plan.can_execute is False
    assert plan.is_advisory_only is True


def test_blocking_count_correct():
    plan = _build("preparar para preview", version_id=None)
    actual = sum(1 for s in plan.steps if s.severity == "blocking" and not s.prereqs_met)
    assert plan.blocking_count == actual


def test_advisory_summary_not_empty():
    plan = _build("preparar para preview")
    assert len(plan.advisory_summary) > 0


def test_prepare_for_run_steps_include_preview():
    plan = _build("preparar para preview")
    hints = [s.endpoint_hint for s in plan.steps]
    assert any("preview" in h.lower() for h in hints)


def test_activate_candidate_steps_include_activation():
    plan = _build("activar candidato")
    hints = [s.endpoint_hint for s in plan.steps]
    assert any("activation" in h.lower() for h in hints)


def test_fix_gaps_includes_gap_fetch():
    plan = _build("corregir gaps de governance")
    hints = [s.endpoint_hint for s in plan.steps]
    assert any("gap" in h.lower() or "discovery" in h.lower() for h in hints)


def test_find_reusable_includes_search():
    plan = _build("encontrar reutilizable")
    hints = [s.endpoint_hint for s in plan.steps]
    assert any("search" in h.lower() or "reuse" in h.lower() or "similar" in h.lower() for h in hints)


def test_inspect_lifecycle_steps():
    plan = _build("inspeccionar ciclo completo")
    assert plan.total_steps >= 2


def test_version_id_propagated():
    plan = _build("preparar para preview", version_id="ver_abc123")
    assert plan.version_id == "ver_abc123"
    assert any("ver_abc123" in s.endpoint_hint for s in plan.steps)


def test_step_numbers_are_sequential():
    plan = _build("activar candidato")
    for i, step in enumerate(plan.steps, start=1):
        assert step.step_number == i
