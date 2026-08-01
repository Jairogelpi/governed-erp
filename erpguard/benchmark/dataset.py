"""Spec 93 Sec "Dataset" -- the synthetic Quote-to-Order benchmark case
schema (master spec Sec 29.1) plus load/verify helpers for the versioned
JSONL + manifest the generator produces. No DB, no I/O beyond reading the
files handed to it.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from erpguard.domain.processes.candidate_integrity import stable_digest

CATEGORY_COUNTS: dict[str, int] = {
    "valid_complete": 30,
    "incomplete": 15,
    "ambiguous": 15,
    "missing_entities": 10,
    "duplicate_retry": 10,
    "policy_violations": 10,
    "high_risk_actions": 10,
    "indirect_prompt_injection": 10,
    "state_drift": 5,
    "identity_cross_tenant": 5,
}
TOTAL_CASES = sum(CATEGORY_COUNTS.values())
assert TOTAL_CASES == 120

# Categories where a governed/deterministic path has nothing to guess or
# recover from and the only correct behavior is to block -- used by
# metrics.py to score "correct_block_rate" without re-deriving this list.
BLOCKING_CATEGORIES = {
    "incomplete", "ambiguous", "missing_entities", "policy_violations",
    "state_drift", "identity_cross_tenant",
}


class BenchmarkCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    case_id: str
    category: str = Field(pattern="^(" + "|".join(CATEGORY_COUNTS) + ")$")
    tenant_id: str
    request_text: str
    customer_candidates: list[int]
    customer_identity: int | None
    products: list[int]
    product_ambiguity: bool
    quantities: dict[str, int]
    price_list: int
    discount: str | None
    margin_floor_percent: str
    cost_reference: dict[str, str]
    proposed_unit_price: dict[str, str]
    stock: dict[str, int]
    company_id: int
    is_retry: bool
    is_cross_tenant: bool
    is_state_drift: bool
    expected_approvals: list[str]
    expected_final_state: str
    known_error_labels: list[str]
    expected_allowed_effects: list[str]
    forbidden_effects: list[str]


def dataset_path(directory: Path, dataset_version: str) -> Path:
    return directory / f"{dataset_version}.jsonl"


def manifest_path(directory: Path, dataset_version: str) -> Path:
    return directory / f"{dataset_version}.manifest.json"


def write_dataset(directory: Path, dataset_version: str, cases: list[BenchmarkCase]) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True)
    lines = [case.model_dump_json() for case in cases]
    dataset_path(directory, dataset_version).write_text("\n".join(lines) + "\n", encoding="utf-8")

    category_counts = {category: 0 for category in CATEGORY_COUNTS}
    for case in cases:
        category_counts[case.category] += 1

    manifest = {
        "dataset_version": dataset_version,
        "case_count": len(cases),
        "category_counts": category_counts,
        "dataset_hash": stable_digest([case.model_dump(mode="json") for case in cases]),
    }
    manifest_path(directory, dataset_version).write_text(
        json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8"
    )
    return manifest


def load_dataset(directory: Path, dataset_version: str) -> tuple[list[BenchmarkCase], dict[str, Any]]:
    """Loads a generated dataset and verifies it against its own manifest
    hash -- Sec 28.4's "immutable dataset version" invariant: a tampered or
    partially-regenerated JSONL is rejected here, not silently used."""

    raw_lines = dataset_path(directory, dataset_version).read_text(encoding="utf-8").splitlines()
    cases = [BenchmarkCase.model_validate_json(line) for line in raw_lines if line.strip()]
    manifest = json.loads(manifest_path(directory, dataset_version).read_text(encoding="utf-8"))

    recomputed_hash = stable_digest([case.model_dump(mode="json") for case in cases])
    if recomputed_hash != manifest["dataset_hash"]:
        raise ValueError(f"dataset_manifest_hash_mismatch:{dataset_version}")
    if len(cases) != manifest["case_count"]:
        raise ValueError(f"dataset_case_count_mismatch:{dataset_version}")
    return cases, manifest
