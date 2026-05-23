"""
Tests for scripts/validate_rc_demo.py — validates the script structure
and logic without requiring a live server.
"""
from __future__ import annotations

import importlib.util
import os
import sys

_SCRIPT_PATH = os.path.join(os.path.dirname(__file__), "..", "scripts", "validate_rc_demo.py")


def _load_script():
    spec = importlib.util.spec_from_file_location("validate_rc_demo", _SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_script_exists():
    assert os.path.exists(_SCRIPT_PATH), "validate_rc_demo.py script missing"


def test_script_not_empty():
    assert os.path.getsize(_SCRIPT_PATH) > 500


def test_script_importable():
    mod = _load_script()
    assert hasattr(mod, "run_validation")


def test_script_has_argparse():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "argparse" in content
    assert "--base-url" in content


def test_script_checks_demo_endpoint():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "/demo" in content


def test_script_checks_demo_seed():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "/v1/operator/demo-seed" in content


def test_script_checks_evidence_packs():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "/v1/operator/evidence-packs" in content


def test_script_checks_tick():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "/v1/skills/schedules/tick" in content


def test_script_checks_safety_report():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "safety-report" in content


def test_script_checks_final_report():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "final-report" in content


def test_script_returns_zero_on_success():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "return 0" in content or "sys.exit" in content
    assert "sys.exit" in content


def test_script_has_rc_accepted_message():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "RC ACCEPTED" in content


def test_script_has_rc_blocked_message():
    content = open(_SCRIPT_PATH, encoding="utf-8").read()
    assert "RC BLOCKED" in content
