from __future__ import annotations

from erpguard.product.ui_selector_candidate import (
    best_selector,
    redact_secret_value,
    normalize_selector,
)


def test_best_selector_prefers_data_testid():
    candidate = best_selector({"data-testid": "order-search", "aria-label": "Search"})
    assert candidate is not None
    assert candidate.selector == "[data-testid='order-search']"
    assert candidate.attr_used == "data-testid"
    assert candidate.confidence == "high"


def test_best_selector_falls_back_to_aria_label():
    candidate = best_selector({"aria-label": "Open order", "name": "open"})
    assert candidate is not None
    assert candidate.selector == "[aria-label='Open order']"
    assert candidate.attr_used == "aria-label"
    assert candidate.confidence == "medium"


def test_best_selector_falls_back_to_name():
    candidate = best_selector({"name": "q"})
    assert candidate is not None
    assert candidate.selector == "[name='q']"
    assert candidate.attr_used == "name"


def test_best_selector_falls_back_to_placeholder():
    candidate = best_selector({"placeholder": "Search order"})
    assert candidate is not None
    assert candidate.selector == "[placeholder='Search order']"
    assert candidate.attr_used == "placeholder"


def test_best_selector_falls_back_to_text():
    candidate = best_selector({}, tag="button", text="Review Formula")
    assert candidate is not None
    assert "Review Formula" in candidate.selector
    assert candidate.confidence == "low"


def test_best_selector_returns_none_for_empty():
    candidate = best_selector({}, tag="", text="")
    assert candidate is None


def test_redact_password_type():
    result = redact_secret_value("q", "password", "mysecret")
    assert result == "[REDACTED]"


def test_redact_field_named_token():
    result = redact_secret_value("api_token", "text", "tok_abc123")
    assert result == "[REDACTED]"


def test_redact_field_named_secret():
    result = redact_secret_value("client_secret", "text", "supersecret")
    assert result == "[REDACTED]"


def test_redact_does_not_redact_normal_field():
    result = redact_secret_value("order_reference", "text", "SO-VALID")
    assert result == "SO-VALID"


def test_redact_does_not_redact_search_field():
    result = redact_secret_value("q", "search", "SO-VALID")
    assert result == "SO-VALID"


def test_normalize_selector_strips_whitespace():
    assert normalize_selector("  [data-testid='btn']  ") == "[data-testid='btn']"


def test_normalize_selector_returns_none_for_none():
    assert normalize_selector(None) is None


def test_normalize_selector_returns_none_for_empty():
    assert normalize_selector("") is None
