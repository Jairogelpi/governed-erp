from __future__ import annotations

from erpguard.product.ui_failure_classifier import UIFailureClassifier


def test_all_checks_pass_returns_no_failure():
    svc = UIFailureClassifier()
    result = svc.classify(
        page_state_ok=True, record_identity_ok=True,
        selector_ambiguity_ok=True, modal_error_ok=True, post_state_ok=True,
    )
    assert result.failure_type == "no_failure"
    assert result.severity == "none"


def test_page_state_fail_with_not_on_fake_erp_returns_wrong_target():
    svc = UIFailureClassifier()
    result = svc.classify(
        page_state_ok=False, record_identity_ok=True,
        selector_ambiguity_ok=True, modal_error_ok=True, post_state_ok=True,
        page_detail="current_url_not_on_fake_erp",
    )
    assert result.failure_type == "wrong_target"
    assert result.severity == "critical"


def test_page_state_fail_with_mismatch_returns_wrong_page():
    svc = UIFailureClassifier()
    result = svc.classify(
        page_state_ok=False, record_identity_ok=True,
        selector_ambiguity_ok=True, modal_error_ok=True, post_state_ok=True,
        page_detail="page_url_mismatch",
    )
    assert result.failure_type == "wrong_page"
    assert result.severity == "error"


def test_record_identity_fail_returns_wrong_record():
    svc = UIFailureClassifier()
    result = svc.classify(
        page_state_ok=True, record_identity_ok=False,
        selector_ambiguity_ok=True, modal_error_ok=True, post_state_ok=True,
        record_detail="unknown_order_reference",
    )
    assert result.failure_type == "wrong_record"


def test_missing_selector_fail_returns_missing_selector():
    svc = UIFailureClassifier()
    result = svc.classify(
        page_state_ok=True, record_identity_ok=True,
        selector_ambiguity_ok=False, modal_error_ok=True, post_state_ok=True,
        selector_detail="missing_selector",
    )
    assert result.failure_type == "missing_selector"


def test_ambiguous_selector_returns_ambiguous_selector():
    svc = UIFailureClassifier()
    result = svc.classify(
        page_state_ok=True, record_identity_ok=True,
        selector_ambiguity_ok=False, modal_error_ok=True, post_state_ok=True,
        selector_detail="text_based_selector_is_ambiguous",
    )
    assert result.failure_type == "ambiguous_selector"
    assert result.severity == "warning"


def test_modal_error_fail_returns_unexpected_modal():
    svc = UIFailureClassifier()
    result = svc.classify(
        page_state_ok=True, record_identity_ok=True,
        selector_ambiguity_ok=True, modal_error_ok=False, post_state_ok=True,
        modal_detail="order_state_blocks_guard",
    )
    assert result.failure_type == "unexpected_modal"


def test_post_state_fail_returns_state_mismatch():
    svc = UIFailureClassifier()
    result = svc.classify(
        page_state_ok=True, record_identity_ok=True,
        selector_ambiguity_ok=True, modal_error_ok=True, post_state_ok=False,
        post_detail="url_did_not_change",
    )
    assert result.failure_type == "state_mismatch"
    assert result.severity == "warning"
