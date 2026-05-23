"""
RC Docs Contract — validates that all RC documentation files exist and
contain the required sections.
"""
from __future__ import annotations

import os

_RELEASE_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "release")
_DEMO_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "demo")

_RELEASE_DOCS = [
    "07_rc_validation_rehearsal.md",
    "08_rc_gap_log.md",
    "09_rc_acceptance_report.md",
]

_DEMO_DOCS = [
    "00_operator_demo_overview.md",
    "01_end_to_end_scenario.md",
    "02_operator_runbook.md",
    "03_safety_boundaries.md",
    "04_failure_modes.md",
    "05_release_evidence_pack.md",
    "06_tfm_defense_script.md",
]


def _read(path: str) -> str:
    return open(path, encoding="utf-8").read()


def test_release_docs_exist():
    for fname in _RELEASE_DOCS:
        path = os.path.join(_RELEASE_DIR, fname)
        assert os.path.exists(path), f"Missing RC release doc: {fname}"


def test_release_docs_not_empty():
    for fname in _RELEASE_DOCS:
        path = os.path.join(_RELEASE_DIR, fname)
        if os.path.exists(path):
            assert os.path.getsize(path) > 200, f"RC doc too small: {fname}"


def test_demo_docs_exist():
    for fname in _DEMO_DOCS:
        path = os.path.join(_DEMO_DIR, fname)
        assert os.path.exists(path), f"Missing demo doc: {fname}"


def test_rehearsal_doc_has_all_steps():
    content = _read(os.path.join(_RELEASE_DIR, "07_rc_validation_rehearsal.md"))
    for step in range(0, 8):
        assert f"Step {step}" in content, f"Step {step} missing from rehearsal doc"


def test_rehearsal_doc_mentions_demo_seed():
    content = _read(os.path.join(_RELEASE_DIR, "07_rc_validation_rehearsal.md"))
    assert "/v1/operator/demo-seed" in content


def test_rehearsal_doc_mentions_tick():
    content = _read(os.path.join(_RELEASE_DIR, "07_rc_validation_rehearsal.md"))
    assert "/v1/skills/schedules/tick" in content or "tick" in content.lower()


def test_gap_log_has_summary():
    content = _read(os.path.join(_RELEASE_DIR, "08_rc_gap_log.md"))
    assert "No blocking gaps" in content or "Gap Register" in content


def test_acceptance_report_has_pass_criteria():
    content = _read(os.path.join(_RELEASE_DIR, "09_rc_acceptance_report.md"))
    assert "PASS" in content
    assert "verdict" in content.lower() or "safe" in content.lower()


def test_acceptance_report_has_explicit_exclusions():
    content = _read(os.path.join(_RELEASE_DIR, "09_rc_acceptance_report.md"))
    assert "Explicit Exclusions" in content or "exclusion" in content.lower()
    assert "LLM" in content or "llm" in content.lower()


def test_acceptance_report_status_accepted():
    content = _read(os.path.join(_RELEASE_DIR, "09_rc_acceptance_report.md"))
    assert "ACCEPTED" in content


def test_acceptance_report_covers_sprint_range():
    content = _read(os.path.join(_RELEASE_DIR, "09_rc_acceptance_report.md"))
    for sprint in range(20, 27):
        assert str(sprint) in content, f"Sprint {sprint} not mentioned in acceptance report"


def test_rehearsal_result_stated():
    content = _read(os.path.join(_RELEASE_DIR, "07_rc_validation_rehearsal.md"))
    assert "passed" in content.lower() or "result" in content.lower()
