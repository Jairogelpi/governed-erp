"""Spec 93 Sec 28.4 -- report regenerated twice from the same raw results
is identical; a changed raw result changes the report. Proves the report
is derived from data, not cached/hand-edited prose."""

from __future__ import annotations

from erpguard.benchmark.dataset_generator import generate_cases
from erpguard.benchmark.report import generate_report
from erpguard.benchmark.runner import run_benchmark


def _rows():
    cases = generate_cases(seed=21)
    return run_benchmark(cases=cases, configurations=["fixed_workflow", "erpguard_candidate"], repeats=1)


def test_report_is_deterministic_from_the_same_raw_rows():
    rows = _rows()
    report_a = generate_report(rows, dataset_version="v_test")
    report_b = generate_report(rows, dataset_version="v_test")
    assert report_a == report_b


def test_report_changes_when_a_raw_result_changes():
    rows = _rows()
    report_a = generate_report(rows, dataset_version="v_test")

    configuration, repeat_index, outcome = rows[0]
    mutated_outcome = outcome.model_copy(update={"task_success": not outcome.task_success})
    mutated_rows = [(configuration, repeat_index, mutated_outcome), *rows[1:]]
    report_b = generate_report(mutated_rows, dataset_version="v_test")

    assert report_a != report_b


def test_report_contains_the_no_fabricated_claims_disclaimer():
    rows = _rows()
    report = generate_report(rows, dataset_version="v_test")
    assert "commercial conversion" in report["disclaimer"]


def test_report_erpguard_candidate_never_less_safe_than_fixed_workflow():
    rows = _rows()
    report = generate_report(rows, dataset_version="v_test")
    fixed = report["configurations"]["fixed_workflow"]["metrics"]["unsafe_side_effect_rate"]
    governed = report["configurations"]["erpguard_candidate"]["metrics"]["unsafe_side_effect_rate"]
    assert governed <= fixed
    assert governed == 0.0


def test_report_flags_not_run_configurations_explicitly():
    rows = _rows()
    from erpguard.benchmark.configurations import direct_tool_agent
    from erpguard.benchmark.fake_erp_store import FakeErpStore

    case = generate_cases(seed=21)[0]
    not_run_outcome = direct_tool_agent.run_case(case, FakeErpStore())
    rows_with_not_run = [*rows, ("direct_tool_agent", 0, not_run_outcome)]
    report = generate_report(rows_with_not_run, dataset_version="v_test")
    assert report["configurations"]["direct_tool_agent"]["not_run_rate"] == 1.0
