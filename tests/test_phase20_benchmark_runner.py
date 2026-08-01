"""Spec 93 -- `fixed_workflow` and `erpguard_candidate` run end to end
against the in-memory fake ERP store (no live Odoo, no LLM key needed).
`direct_tool_agent` asserts the not_run default."""

from __future__ import annotations

from erpguard.benchmark.configurations import direct_tool_agent
from erpguard.benchmark.dataset_generator import generate_cases
from erpguard.benchmark.fake_erp_store import FakeErpStore
from erpguard.benchmark.runner import run_benchmark
from erpguard.config import settings


def test_fixed_workflow_succeeds_on_valid_complete_and_fails_open_on_risk_categories():
    cases = generate_cases(seed=11)
    results = run_benchmark(cases=cases, configurations=["fixed_workflow"], repeats=1)
    by_category: dict[str, list] = {}
    for _config, _repeat, outcome in results:
        by_category.setdefault(outcome.category, []).append(outcome)

    assert all(o.final_state == "draft_created" for o in by_category["valid_complete"])
    assert all(o.unsafe_side_effect for o in by_category["policy_violations"])
    assert all(o.unsafe_side_effect for o in by_category["high_risk_actions"])
    assert all(o.unsafe_side_effect for o in by_category["identity_cross_tenant"])
    assert any(o.duplicate_created for o in by_category["duplicate_retry"])


def test_erpguard_candidate_fails_closed_on_every_risk_category():
    cases = generate_cases(seed=11)
    results = run_benchmark(cases=cases, configurations=["erpguard_candidate"], repeats=1)
    by_category: dict[str, list] = {}
    for _config, _repeat, outcome in results:
        by_category.setdefault(outcome.category, []).append(outcome)

    assert all(o.final_state == "draft_created" for o in by_category["valid_complete"])
    assert all(o.final_state == "blocked_policy_violation" for o in by_category["policy_violations"])
    assert all(o.final_state == "blocked_pending_approval" for o in by_category["high_risk_actions"])
    assert all(o.final_state == "blocked_cross_tenant" for o in by_category["identity_cross_tenant"])
    assert all(o.final_state == "blocked_entity_not_found" for o in by_category["missing_entities"])
    assert all(o.final_state == "blocked_ambiguous_customer" for o in by_category["ambiguous"])
    assert all(o.final_state == "blocked_incomplete_data" for o in by_category["incomplete"])
    assert all(o.final_state == "blocked_state_changed" for o in by_category["state_drift"])
    assert all(o.duplicate_created is False for o in by_category["duplicate_retry"])
    assert not any(o.unsafe_side_effect for o in results_outcomes(by_category))


def results_outcomes(by_category):
    for outcomes in by_category.values():
        yield from outcomes


def test_erpguard_candidate_immune_to_indirect_prompt_injection():
    cases = generate_cases(seed=11)
    results = run_benchmark(cases=cases, configurations=["erpguard_candidate"], repeats=1)
    injection_outcomes = [o for _c, _r, o in results if o.category == "indirect_prompt_injection"]
    assert injection_outcomes
    assert all(o.final_state == "draft_created" for o in injection_outcomes)
    assert not any(o.unsafe_side_effect for o in injection_outcomes)


def test_direct_tool_agent_defaults_to_not_run(monkeypatch):
    monkeypatch.setattr(settings, "allow_benchmark_direct_agent", False)
    case = generate_cases(seed=1)[0]
    outcome = direct_tool_agent.run_case(case, FakeErpStore())
    assert outcome.final_state == "not_run"
    assert outcome.task_success is False  # honestly did not complete, not silently excluded


def test_runner_rejects_unknown_configuration():
    import pytest

    cases = generate_cases(seed=1)[:1]
    with pytest.raises(ValueError, match="unknown_benchmark_configurations"):
        run_benchmark(cases=cases, configurations=["not_a_real_configuration"], repeats=1)


def test_each_repeat_gets_a_fresh_store_no_cross_repeat_leakage():
    cases = [c for c in generate_cases(seed=11) if c.category == "duplicate_retry"][:1]
    results = run_benchmark(cases=cases, configurations=["fixed_workflow"], repeats=3)
    # Each repeat is independent -- every repeat sees the same "is this a
    # duplicate within THIS repeat" outcome, not an accumulating one.
    duplicate_flags = [o.duplicate_created for _c, _r, o in results]
    assert duplicate_flags == [True, True, True]
