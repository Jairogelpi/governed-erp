"""Sprint 44 — Action registry tests."""
from __future__ import annotations

import pytest

from erpguard.product.operator_action_registry import (
    get_action_entry,
    list_all_actions,
    normalize_to_action_key,
)

EXPECTED_KEYS = {
    "check_governance_gaps",
    "record_human_decision",
    "create_activation_request",
    "evaluate_final_gate",
    "activate_candidate",
    "run_preview",
    "search_skills",
    "reuse_suggestions",
    "inspect_lifecycle",
}


def test_all_expected_keys_present():
    keys = {a.action_key for a in list_all_actions()}
    assert EXPECTED_KEYS <= keys


def test_registry_count():
    assert len(list_all_actions()) >= 9


def test_get_action_entry_known():
    entry = get_action_entry("activate_candidate")
    assert entry is not None
    assert entry.action_key == "activate_candidate"
    assert entry.safety_tier == "activation_only"
    assert entry.requires_confirmed_token is True
    assert entry.allowed is True


def test_get_action_entry_unknown():
    assert get_action_entry("nonexistent_key") is None


def test_read_only_actions_no_token_required():
    for key in ("check_governance_gaps", "evaluate_final_gate", "search_skills",
                "reuse_suggestions", "inspect_lifecycle"):
        e = get_action_entry(key)
        assert e.requires_confirmed_token is False, f"{key} should not require token"
        assert e.safety_tier == "read_only"


def test_mutating_actions_require_token():
    for key in ("record_human_decision", "create_activation_request",
                "activate_candidate", "run_preview"):
        e = get_action_entry(key)
        assert e.requires_confirmed_token is True, f"{key} should require token"


@pytest.mark.parametrize("endpoint,method,expected", [
    ("GET /v1/agent-builder/discovery/gaps/ver_1", "GET", "check_governance_gaps"),
    ("POST /v1/agent-candidate-decision/ver_1", "POST", "record_human_decision"),
    ("POST /v1/agent-candidate-activation-request/ver_1", "POST", "create_activation_request"),
    ("GET /v1/agent-builder/advisory/evaluate-final-gate/ver_1", "GET", "evaluate_final_gate"),
    ("POST /v1/agent-candidate-activation/ver_1", "POST", "activate_candidate"),
    ("POST /v1/agent-skill-run-preview/ver_1/run", "POST", "run_preview"),
    ("GET /v1/agent-builder/discovery/search?query=foo", "GET", "search_skills"),
    ("GET /v1/agent-builder/discovery/reuse?version_id=ver_1", "GET", "reuse_suggestions"),
    ("GET /v1/agent-builder/advisory/lifecycle-summary/ver_1", "GET", "inspect_lifecycle"),
])
def test_normalization(endpoint, method, expected):
    result = normalize_to_action_key(endpoint, method)
    assert result == expected, f"endpoint={endpoint!r} expected={expected} got={result}"


def test_normalization_unknown_returns_none():
    assert normalize_to_action_key("GET /v1/some/random/path", "GET") is None


def test_all_entries_have_endpoint_template():
    for a in list_all_actions():
        assert len(a.endpoint_template) > 0


def test_all_entries_have_description():
    for a in list_all_actions():
        assert len(a.description) > 0
