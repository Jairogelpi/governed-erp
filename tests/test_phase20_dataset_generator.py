"""Spec 93 -- dataset generator determinism, field completeness, category
distribution."""

from __future__ import annotations

import tempfile
from pathlib import Path

from erpguard.benchmark.dataset import CATEGORY_COUNTS, TOTAL_CASES, load_dataset, write_dataset
from erpguard.benchmark.dataset_generator import generate_cases


def test_generates_exactly_120_cases_with_the_spec_distribution():
    cases = generate_cases(seed=1)
    assert len(cases) == TOTAL_CASES == 120

    counts: dict[str, int] = {}
    for case in cases:
        counts[case.category] = counts.get(case.category, 0) + 1
    assert counts == CATEGORY_COUNTS


def test_same_seed_produces_identical_cases():
    cases_a = generate_cases(seed=42)
    cases_b = generate_cases(seed=42)
    assert [c.model_dump(mode="json") for c in cases_a] == [c.model_dump(mode="json") for c in cases_b]


def test_different_seed_produces_different_cases():
    cases_a = generate_cases(seed=1)
    cases_b = generate_cases(seed=2)
    assert [c.model_dump(mode="json") for c in cases_a] != [c.model_dump(mode="json") for c in cases_b]


def test_every_case_has_the_required_sec_29_1_fields():
    cases = generate_cases(seed=7)
    for case in cases:
        assert case.case_id
        assert case.category in CATEGORY_COUNTS
        assert case.request_text
        assert isinstance(case.customer_candidates, list)
        assert isinstance(case.products, list)
        assert case.expected_final_state
        assert isinstance(case.known_error_labels, list)
        assert isinstance(case.expected_allowed_effects, list)
        assert isinstance(case.forbidden_effects, list)


def test_incomplete_cases_are_genuinely_missing_data():
    cases = [c for c in generate_cases(seed=7) if c.category == "incomplete"]
    assert cases
    assert all(c.quantities == {} for c in cases)


def test_missing_entities_cases_reference_a_nonexistent_customer():
    cases = [c for c in generate_cases(seed=7) if c.category == "missing_entities"]
    assert cases
    assert all(c.customer_identity == 9999 for c in cases)


def test_ambiguous_cases_have_multiple_candidates_and_no_resolved_identity():
    cases = [c for c in generate_cases(seed=7) if c.category == "ambiguous"]
    assert cases
    assert all(len(c.customer_candidates) > 1 and c.customer_identity is None for c in cases)


def test_indirect_prompt_injection_cases_carry_an_injection_phrase():
    cases = [c for c in generate_cases(seed=7) if c.category == "indirect_prompt_injection"]
    assert cases
    assert all(
        any(phrase in c.request_text for phrase in ("Ignore all previous", "SYSTEM:", "Disregard the margin"))
        for c in cases
    )


def test_write_and_load_dataset_round_trips_and_verifies_hash():
    cases = generate_cases(seed=9)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        manifest = write_dataset(directory, "v_test", cases)
        loaded_cases, loaded_manifest = load_dataset(directory, "v_test")
        assert len(loaded_cases) == len(cases)
        assert loaded_manifest["dataset_hash"] == manifest["dataset_hash"]


def test_load_dataset_rejects_a_tampered_jsonl():
    cases = generate_cases(seed=9)
    with tempfile.TemporaryDirectory() as tmp:
        directory = Path(tmp)
        write_dataset(directory, "v_test", cases)
        from erpguard.benchmark.dataset import dataset_path

        path = dataset_path(directory, "v_test")
        lines = path.read_text(encoding="utf-8").splitlines()
        lines.pop()  # remove one case -- tamper
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        import pytest
        with pytest.raises(ValueError, match="dataset_manifest_hash_mismatch|dataset_case_count_mismatch"):
            load_dataset(directory, "v_test")
