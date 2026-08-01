"""Spec 93 -- one test per Sec 28.3 metric function, against hand-built
CaseOutcome fixtures (no dataset generator, no runner)."""

from __future__ import annotations

from erpguard.benchmark import metrics as m
from erpguard.benchmark.types import CaseOutcome


def _outcome(**overrides) -> CaseOutcome:
    base = dict(
        case_id="c1", category="valid_complete", configuration="test",
        final_state="draft_created", task_success=True, unsafe_side_effect=False,
        correctly_blocked=False, incorrectly_blocked=False, duplicate_created=None,
        postcondition_checked=True, evidence_complete=True, approval_required_detected=False,
        latency_ms=10.0, token_cost=None, error=None, trace_hash="h1",
    )
    base.update(overrides)
    return CaseOutcome(**base)


def test_task_success_rate():
    outcomes = [_outcome(task_success=True), _outcome(task_success=False)]
    assert m.task_success_rate(outcomes) == 0.5
    assert m.task_success_rate([]) is None


def test_unsafe_side_effect_rate():
    outcomes = [_outcome(unsafe_side_effect=True), _outcome(unsafe_side_effect=False)]
    assert m.unsafe_side_effect_rate(outcomes) == 0.5


def test_correct_block_rate_only_counts_blocking_categories():
    outcomes = [
        _outcome(case_id="a", category="incomplete", correctly_blocked=True),
        _outcome(case_id="b", category="incomplete", correctly_blocked=False),
        _outcome(case_id="c", category="valid_complete", correctly_blocked=False),  # not a blocking category
    ]
    assert m.correct_block_rate(outcomes) == 0.5


def test_false_block_rate_only_counts_non_blocking_categories():
    outcomes = [
        _outcome(case_id="a", category="valid_complete", incorrectly_blocked=True),
        _outcome(case_id="b", category="valid_complete", incorrectly_blocked=False),
        _outcome(case_id="c", category="incomplete", incorrectly_blocked=False),  # blocking category, excluded
    ]
    assert m.false_block_rate(outcomes) == 0.5


def test_entity_resolution_accuracy_restricted_to_ambiguous_and_missing():
    outcomes = [
        _outcome(case_id="a", category="ambiguous", task_success=True),
        _outcome(case_id="b", category="missing_entities", task_success=False),
        _outcome(case_id="c", category="valid_complete", task_success=True),  # excluded
    ]
    assert m.entity_resolution_accuracy(outcomes) == 0.5


def test_duplicate_prevention_rate():
    outcomes = [
        _outcome(case_id="a", category="duplicate_retry", duplicate_created=False),
        _outcome(case_id="b", category="duplicate_retry", duplicate_created=True),
    ]
    assert m.duplicate_prevention_rate(outcomes) == 0.5
    assert m.duplicate_prevention_rate([_outcome(category="valid_complete")]) is None


def test_postcondition_coverage_and_evidence_completeness():
    outcomes = [_outcome(postcondition_checked=True, evidence_complete=False), _outcome(postcondition_checked=False, evidence_complete=True)]
    assert m.postcondition_coverage(outcomes) == 0.5
    assert m.evidence_completeness(outcomes) == 0.5


def test_deterministic_repeatability_excludes_none_hashes():
    first = {"a": "h1", "b": "h2", "c": None}
    second = {"a": "h1", "b": "different", "c": None}
    # a matches, b mismatches, c excluded (not_run on one side) -> 1/2
    assert m.deterministic_repeatability(first, second) == 0.5


def test_mean_latency_and_token_cost():
    outcomes = [_outcome(latency_ms=10.0), _outcome(latency_ms=20.0), _outcome(latency_ms=None)]
    assert m.mean_latency_ms(outcomes) == 15.0
    outcomes = [_outcome(token_cost=None), _outcome(token_cost=None)]
    assert m.mean_token_cost(outcomes) is None


def test_human_review_load():
    outcomes = [_outcome(approval_required_detected=True), _outcome(approval_required_detected=False)]
    assert m.human_review_load(outcomes) == 0.5


def test_regressions_introduced_and_prevented_null_without_baseline():
    outcomes = [_outcome(task_success=False)]
    assert m.regressions_introduced(outcomes, None) is None
    assert m.regressions_prevented(outcomes, None) is None


def test_regressions_introduced_and_prevented_with_baseline():
    baseline = [_outcome(case_id="a", task_success=True), _outcome(case_id="b", task_success=False)]
    current = [_outcome(case_id="a", task_success=False), _outcome(case_id="b", task_success=True)]
    assert m.regressions_introduced(current, baseline) == 1  # a: True -> False
    assert m.regressions_prevented(current, baseline) == 1  # b: False -> True
