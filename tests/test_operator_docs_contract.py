from __future__ import annotations

import os

_DOCS_DIR = os.path.join(os.path.dirname(__file__), "..", "docs", "demo")

_EXPECTED_DOCS = [
    "00_operator_demo_overview.md",
    "01_end_to_end_scenario.md",
    "02_operator_runbook.md",
    "03_safety_boundaries.md",
    "04_failure_modes.md",
    "05_release_evidence_pack.md",
    "06_tfm_defense_script.md",
]


def test_all_doc_files_exist():
    for fname in _EXPECTED_DOCS:
        path = os.path.join(_DOCS_DIR, fname)
        assert os.path.exists(path), f"Missing doc file: {fname}"


def test_doc_files_not_empty():
    for fname in _EXPECTED_DOCS:
        path = os.path.join(_DOCS_DIR, fname)
        if os.path.exists(path):
            assert os.path.getsize(path) > 100, f"Doc file too small: {fname}"


def test_overview_contains_loop():
    path = os.path.join(_DOCS_DIR, "00_operator_demo_overview.md")
    content = open(path, encoding="utf-8").read()
    assert "Sprint 20" in content or "20" in content
    assert "Sprint 26" in content or "26" in content


def test_safety_boundaries_lists_invariants():
    path = os.path.join(_DOCS_DIR, "03_safety_boundaries.md")
    content = open(path, encoding="utf-8").read()
    assert "Fake ERP only" in content
    assert "No LLM" in content or "No LLM at replay" in content
    assert "enforced" in content


def test_failure_modes_lists_categories():
    path = os.path.join(_DOCS_DIR, "04_failure_modes.md")
    content = open(path, encoding="utf-8").read()
    assert "Recording" in content
    assert "Replay" in content
    assert "Scheduler" in content


def test_runbook_documents_tick():
    path = os.path.join(_DOCS_DIR, "02_operator_runbook.md")
    content = open(path, encoding="utf-8").read()
    assert "tick" in content.lower()
    assert "/v1/skills/schedules/tick" in content


def test_evidence_pack_lists_sprints():
    path = os.path.join(_DOCS_DIR, "05_release_evidence_pack.md")
    content = open(path, encoding="utf-8").read()
    for sprint in range(20, 27):
        assert str(sprint) in content, f"Sprint {sprint} missing from evidence pack doc"


def test_defense_script_has_qa_section():
    path = os.path.join(_DOCS_DIR, "06_tfm_defense_script.md")
    content = open(path, encoding="utf-8").read()
    assert "Q&A" in content or "Q&amp;A" in content or "QA" in content.upper()
    assert "LLM" in content


def test_end_to_end_scenario_has_all_steps():
    path = os.path.join(_DOCS_DIR, "01_end_to_end_scenario.md")
    content = open(path, encoding="utf-8").read()
    assert "Record" in content
    assert "Compile" in content or "compile" in content
    assert "replay" in content.lower()
    assert "schedule" in content.lower()
    assert "evidence pack" in content.lower()
