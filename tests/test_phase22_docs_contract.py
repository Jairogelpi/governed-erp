"""Spec 95 (Phase 22) Sec 39.2 -- annex existence contract.

Same discipline as `tests/test_release_docs_contract.py`, extended to the
TFM annex list: this asserts every annex file the master spec's Sec 39.2
requires actually exists at its documented path before the release-gate
script (Sec 32.3: "missing current/simulated capability matrix" is a
blocking criterion, and an incomplete annex set is the same failure mode)
can ever report success. Existence only -- annex *content* quality
(especially `docs/tfm/memoria_draft.md`) is the thesis author's call, not
a CI assertion.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

_REQUIRED_FILES = [
    # Full spec set (84-95).
    "docs/specs/84_erpguard_evolution_master_spec.md",
    "docs/specs/92_governed_decision_to_outcome_backend_rc.md",
    "docs/specs/93_phase20_erpriskbench_and_experiments.md",
    "docs/specs/94_phase21_product_web_application.md",
    "docs/specs/95_phase22_tfm_delivery_and_release_freeze.md",
    # Annex set.
    "docs/tfm/annexes/00_index.md",
    "docs/tfm/annexes/openapi_export.json",
    "docs/tfm/annexes/direct_tool_agent_prompt.md",
    "docs/tfm/annexes/data_rights_and_gdpr.md",
    "docs/tfm/annexes/installation.md",
    "docs/tfm/annexes/code_and_repository.md",
    "docs/tfm/annexes/test_reports/README.md",
    "docs/tfm/annexes/test_reports/latest_pytest_output.txt",
    # Connector SDK / process package pointers.
    "docs/architecture/connector_sdk_v2.md",
    "docs/architecture/quote_to_order_process.md",
    # Threat model.
    "docs/security/operational_canary_threat_model.md",
    # Evidence packs (sanitized).
    "docs/demo/backend_rc_live_pricing_scenario_evidence.json",
    "docs/demo/backend_rc_decision_to_outcome_evidence.json",
    # Benchmark dataset manifest.
    "docs/benchmark/datasets/quote_to_order_v1_seed92.manifest.json",
    # Capability reality matrix (Sec 32.3 release-gate criterion).
    "docs/architecture/capability_reality_matrix.md",
    # TFM memory draft and supporting demo/version docs.
    "docs/tfm/memoria_draft.md",
    "docs/demo/five_minute_demo_script.md",
    "docs/release/versions.md",
    # Clean-install tooling.
    "docker-compose.demo.yml",
    "scripts/validate_demo_install.py",
]


def test_every_annex_file_exists():
    missing = [path for path in _REQUIRED_FILES if not (ROOT / path).exists()]
    assert missing == [], f"Missing annex files: {missing}"


def test_annex_files_are_not_empty():
    empty = [
        path for path in _REQUIRED_FILES
        if (ROOT / path).exists() and (ROOT / path).stat().st_size == 0
    ]
    assert empty == [], f"Empty annex files: {empty}"


def test_benchmark_reports_directory_has_at_least_one_generated_report():
    reports_dir = ROOT / "docs" / "benchmark" / "reports"
    assert reports_dir.is_dir(), "docs/benchmark/reports/ missing -- run scripts/export_benchmark_report.py"
    report_files = list(reports_dir.glob("*.report.json"))
    raw_files = list(reports_dir.glob("*.raw_results.json"))
    assert report_files, "no *.report.json found -- run scripts/export_benchmark_report.py"
    assert raw_files, "no *.raw_results.json found -- run scripts/export_benchmark_report.py"
