"""Spec 93 Sec 28.4 -- "report generated from data, not edited manually."
Aggregates raw `(configuration, repeat_index, CaseOutcome)` rows into the
statistical summary Sec 39.1's "Experiment and results" chapter cites.
Pure function of its input; the caller decides whether that input came
from a fresh run or from persisted `BenchmarkCaseResult` rows -- the
report itself cannot tell the difference, which is the point.
"""

from __future__ import annotations

from typing import Any

from erpguard.benchmark import metrics as m
from erpguard.benchmark.types import CaseOutcome
from erpguard.domain.canary.metrics import wilson_interval

_PROPORTION_METRICS = (
    "task_success_rate", "unsafe_side_effect_rate", "correct_block_rate",
    "false_block_rate", "entity_resolution_accuracy", "duplicate_prevention_rate",
    "postcondition_coverage", "evidence_completeness", "human_review_load",
)


def _group(rows: list[tuple[str, int, CaseOutcome]]) -> dict[str, list[CaseOutcome]]:
    grouped: dict[str, list[CaseOutcome]] = {}
    for configuration, _repeat_index, outcome in rows:
        grouped.setdefault(configuration, []).append(outcome)
    return grouped


def _confidence_interval(rate: float | None, n: int) -> dict[str, float] | None:
    if rate is None or n == 0:
        return None
    return wilson_interval(round(rate * n), n)


def _configuration_summary(outcomes: list[CaseOutcome], baseline: list[CaseOutcome] | None) -> dict[str, Any]:
    n = len(outcomes)
    not_run_count = sum(1 for o in outcomes if o.final_state == "not_run")

    values = {
        "task_success_rate": m.task_success_rate(outcomes),
        "unsafe_side_effect_rate": m.unsafe_side_effect_rate(outcomes),
        "correct_block_rate": m.correct_block_rate(outcomes),
        "false_block_rate": m.false_block_rate(outcomes),
        "entity_resolution_accuracy": m.entity_resolution_accuracy(outcomes),
        "duplicate_prevention_rate": m.duplicate_prevention_rate(outcomes),
        "postcondition_coverage": m.postcondition_coverage(outcomes),
        "evidence_completeness": m.evidence_completeness(outcomes),
        "human_review_load": m.human_review_load(outcomes),
        "mean_latency_ms": m.mean_latency_ms(outcomes),
        "mean_token_cost": m.mean_token_cost(outcomes),
        "regressions_introduced": m.regressions_introduced(outcomes, baseline),
        "regressions_prevented": m.regressions_prevented(outcomes, baseline),
    }
    confidence_intervals = {
        name: _confidence_interval(values[name], n) for name in _PROPORTION_METRICS
    }

    by_category: dict[str, dict[str, Any]] = {}
    categories = sorted({o.category for o in outcomes})
    for category in categories:
        category_outcomes = [o for o in outcomes if o.category == category]
        by_category[category] = {
            "case_count": len(category_outcomes),
            "task_success_rate": m.task_success_rate(category_outcomes),
            "unsafe_side_effect_rate": m.unsafe_side_effect_rate(category_outcomes),
        }

    return {
        "case_count": n,
        "not_run_count": not_run_count,
        "not_run_rate": (not_run_count / n) if n else None,
        "metrics": values,
        "confidence_intervals_95": confidence_intervals,
        "by_category": by_category,
    }


def generate_report(
    rows: list[tuple[str, int, CaseOutcome]],
    *,
    dataset_version: str,
    baseline_rows: list[tuple[str, int, CaseOutcome]] | None = None,
    repeatability: dict[str, float | None] | None = None,
) -> dict[str, Any]:
    grouped = _group(rows)
    baseline_grouped = _group(baseline_rows) if baseline_rows else {}

    summaries = {
        configuration: _configuration_summary(outcomes, baseline_grouped.get(configuration))
        for configuration, outcomes in grouped.items()
    }
    for configuration, rate in (repeatability or {}).items():
        if configuration in summaries:
            summaries[configuration]["metrics"]["deterministic_repeatability"] = rate

    return {
        "dataset_version": dataset_version,
        "disclaimer": (
            "Synthetic Quote-to-Order dataset (Spec 92/93 Sec 29.3): these "
            "results validate governance logic against a controlled, "
            "reproducible case set. They do not prove real commercial "
            "conversion outcomes."
        ),
        "configurations": summaries,
        "comparison": {
            metric: {
                configuration: summaries[configuration]["metrics"].get(metric)
                for configuration in summaries
            }
            for metric in (
                "task_success_rate", "unsafe_side_effect_rate", "correct_block_rate",
                "false_block_rate", "mean_latency_ms", "mean_token_cost",
            )
        },
    }
