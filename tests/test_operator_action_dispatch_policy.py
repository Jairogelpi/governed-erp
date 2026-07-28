"""Sprint 44 — Dispatch policy tests."""
from __future__ import annotations


from erpguard.product.operator_action_dispatch_policy import check_dispatch_policy
from erpguard.product.operator_action_registry import get_action_entry


def _check(key: str, token_confirmed: bool = False):
    return check_dispatch_policy(get_action_entry(key), token_confirmed=token_confirmed)


def test_read_only_always_eligible():
    for key in ("check_governance_gaps", "evaluate_final_gate", "search_skills",
                "reuse_suggestions", "inspect_lifecycle"):
        r = _check(key, token_confirmed=False)
        assert r.allowed is True, f"{key} should be eligible without token"
        assert r.policy_name == "read_only_always_eligible"


def test_activation_blocked_without_token():
    r = _check("activate_candidate", token_confirmed=False)
    assert r.allowed is False
    assert "activation_only" in r.policy_name or "token" in r.policy_name.lower()


def test_activation_eligible_with_token():
    r = _check("activate_candidate", token_confirmed=True)
    assert r.allowed is True


def test_governance_blocked_without_token():
    for key in ("record_human_decision", "create_activation_request"):
        r = _check(key, token_confirmed=False)
        assert r.allowed is False, f"{key} should be blocked without token"


def test_governance_eligible_with_token():
    for key in ("record_human_decision", "create_activation_request"):
        r = _check(key, token_confirmed=True)
        assert r.allowed is True, f"{key} should be eligible with token"


def test_creates_record_blocked_without_token():
    r = _check("run_preview", token_confirmed=False)
    assert r.allowed is False


def test_creates_record_eligible_with_token():
    r = _check("run_preview", token_confirmed=True)
    assert r.allowed is True


def test_policy_result_has_reason():
    for key in ("activate_candidate", "record_human_decision", "run_preview"):
        r = _check(key, token_confirmed=False)
        assert len(r.reason) > 0


def test_policy_result_has_policy_name():
    r = _check("activate_candidate", token_confirmed=False)
    assert len(r.policy_name) > 0
