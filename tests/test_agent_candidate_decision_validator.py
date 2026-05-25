"""Sprint 36 — Agent Candidate Decision Validator unit tests."""
from __future__ import annotations

import pytest
from erpguard.product.agent_candidate_decision_validator import validate_human_decision


def test_valid_approve():
    r = validate_human_decision("approve", "human_reviewer")
    assert r.valid is True
    assert r.issues == []


def test_valid_reject():
    r = validate_human_decision("reject", "human_reviewer", rationale="Not ready")
    assert r.valid is True


def test_valid_request_changes():
    r = validate_human_decision("request_changes", "reviewer", rationale="Needs adjustment")
    assert r.valid is True


def test_invalid_decision_value():
    r = validate_human_decision("activate", "reviewer")
    assert r.valid is False
    assert any("not valid" in i for i in r.issues)


def test_missing_decision():
    r = validate_human_decision("", "reviewer")
    assert r.valid is False
    assert any("required" in i for i in r.issues)


def test_missing_actor():
    r = validate_human_decision("approve", "")
    assert r.valid is False
    assert any("actor" in i for i in r.issues)


def test_request_changes_requires_rationale():
    r = validate_human_decision("request_changes", "reviewer", rationale="")
    assert r.valid is False
    assert any("rationale" in i for i in r.issues)


def test_request_changes_with_rationale_valid():
    r = validate_human_decision("request_changes", "reviewer", rationale="Please fix X")
    assert r.valid is True
