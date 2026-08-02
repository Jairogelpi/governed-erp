"""Spec 95 Sec 32 -- CI "benchmark smoke" gate: a fast confidence check
that the ERPRiskBench harness still runs and produces sane output, not a
re-run of Phase 20's actual 120-case x 3-configuration experiment (that
stays a deliberate, manually-triggered `scripts/export_benchmark_report.py`
/ `POST /v1/benchmarks/runs` action -- CI runs this on every push, so it
has to stay fast and configuration-limited to `erpguard_candidate`, per
Spec 95's own scoping note).
"""
from __future__ import annotations

from pathlib import Path

from erpguard.benchmark.configurations import erpguard_candidate
from erpguard.benchmark.dataset import load_dataset
from erpguard.benchmark.fake_erp_store import FakeErpStore
from erpguard.benchmark.report import generate_report

DATASET_DIR = Path("docs/benchmark/datasets")
DATASET_VERSION = "quote_to_order_v1_seed92"
SMOKE_CASE_COUNT = 8


def test_erpguard_candidate_smoke_runs_a_handful_of_cases_without_crashing():
    cases, manifest = load_dataset(DATASET_DIR, DATASET_VERSION)
    assert manifest["case_count"] == 120, "smoke test expects the committed Sec 93 dataset, not a stand-in"

    sample = cases[:SMOKE_CASE_COUNT]
    store = FakeErpStore()
    outcomes = [erpguard_candidate.run_case(case, store) for case in sample]

    assert len(outcomes) == SMOKE_CASE_COUNT
    for outcome, case in zip(outcomes, sample):
        assert outcome.case_id == case.case_id
        assert outcome.configuration == erpguard_candidate.NAME
        assert outcome.final_state != "not_run", "erpguard_candidate has no external-dependency gate, unlike direct_tool_agent"


def test_erpguard_candidate_smoke_report_generates_without_crashing():
    cases, _manifest = load_dataset(DATASET_DIR, DATASET_VERSION)
    sample = cases[:SMOKE_CASE_COUNT]
    store = FakeErpStore()
    rows = [
        (erpguard_candidate.NAME, 0, erpguard_candidate.run_case(case, store))
        for case in sample
    ]
    report = generate_report(rows, dataset_version=DATASET_VERSION)

    assert erpguard_candidate.NAME in report["configurations"]
    summary = report["configurations"][erpguard_candidate.NAME]
    assert summary["case_count"] == SMOKE_CASE_COUNT
    assert 0.0 <= summary["metrics"]["task_success_rate"] <= 1.0
