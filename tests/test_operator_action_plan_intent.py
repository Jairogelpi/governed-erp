"""Sprint 42 — Action plan intent classifier tests."""
from __future__ import annotations

import pytest

from erpguard.product.operator_action_plan_intent import classify_plan_intent, list_supported_plan_types


@pytest.mark.parametrize("goal,expected", [
    ("quiero preparar para preview la skill", "prepare_for_run"),
    ("prepare for preview", "prepare_for_run"),
    ("listo para ejecutar", "prepare_for_run"),
    ("activar candidato", "activate_candidate"),
    ("activate candidate", "activate_candidate"),
    ("corregir gaps de governance", "fix_governance_gaps"),
    ("fix governance gaps", "fix_governance_gaps"),
    ("encontrar reutilizable", "find_reusable_skill"),
    ("can i reuse something", "find_reusable_skill"),
    ("inspeccionar ciclo de vida completo", "inspect_lifecycle"),
    ("full lifecycle status", "inspect_lifecycle"),
    ("asdfghjkl", "unknown"),
])
def test_classify_plan_intent(goal, expected):
    result = classify_plan_intent(goal)
    assert result.plan_type == expected, f"goal={goal!r} expected={expected} got={result.plan_type}"


def test_confidence_range():
    for goal in ["preparar para preview", "activar", "fix gaps", "reutilizar", "inspeccionar"]:
        r = classify_plan_intent(goal)
        assert 0.0 <= r.confidence <= 1.0


def test_unknown_has_low_confidence():
    r = classify_plan_intent("hello world xyz")
    assert r.confidence <= 0.3


def test_matched_keywords_populated():
    r = classify_plan_intent("preparar para preview")
    assert len(r.matched_keywords) >= 1


def test_list_supported_plan_types_count():
    types = list_supported_plan_types()
    assert len(types) == 6


def test_list_supported_plan_types_fields():
    for t in list_supported_plan_types():
        assert "plan_type" in t
        assert "description" in t


def test_all_supported_types_present():
    names = {t["plan_type"] for t in list_supported_plan_types()}
    for expected in ("prepare_for_run", "activate_candidate", "fix_governance_gaps",
                     "find_reusable_skill", "inspect_lifecycle", "unknown"):
        assert expected in names
