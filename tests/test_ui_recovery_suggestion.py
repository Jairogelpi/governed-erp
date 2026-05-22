from __future__ import annotations

from erpguard.product.ui_recovery_suggestion import UIRecoverySuggestionService


def test_suggest_wrong_target():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("wrong_target")
    assert "fake-erp" in s.lower() or "fake ERP" in s or "Fake ERP" in s


def test_suggest_wrong_page():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("wrong_page")
    assert "navigate" in s.lower() or "expected page" in s.lower()


def test_suggest_wrong_record():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("wrong_record")
    assert "SO-VALID" in s


def test_suggest_missing_selector():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("missing_selector")
    assert "re-record" in s.lower()


def test_suggest_ambiguous_selector():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("ambiguous_selector")
    assert "data-testid" in s.lower()


def test_suggest_unexpected_modal():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("unexpected_modal")
    assert "modal" in s.lower() or "error" in s.lower()
    # suggestion must NOT propose coordinate automation as a solution
    assert "do not use coordinate" in s.lower() or "coordinate automation" in s.lower()


def test_suggest_state_mismatch():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("state_mismatch")
    assert "re-record" in s.lower() or "state" in s.lower()


def test_suggest_no_failure():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("no_failure")
    assert "no recovery" in s.lower() or "passed" in s.lower()


def test_suggest_with_step_context():
    svc = UIRecoverySuggestionService()
    s = svc.suggest("wrong_page", context={"step_id": "step_3"})
    assert "step_3" in s


def test_all_suggestions_covered():
    svc = UIRecoverySuggestionService()
    suggestions = svc.all_suggestions()
    assert "wrong_target" in suggestions
    assert "wrong_page" in suggestions
    assert "wrong_record" in suggestions
    assert "missing_selector" in suggestions
    assert "ambiguous_selector" in suggestions
    assert "unexpected_modal" in suggestions
    assert "state_mismatch" in suggestions
    assert "no_failure" in suggestions
