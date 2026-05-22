from __future__ import annotations

from erpguard.product.ui_selector_ambiguity import UISelectorAmbiguityDetector


def test_navigate_step_skips_selector_check():
    svc = UISelectorAmbiguityDetector()
    result = svc.detect({"type": "navigate"})
    assert result.ok is True


def test_guard_step_skips_selector_check():
    svc = UISelectorAmbiguityDetector()
    result = svc.detect({"type": "guard"})
    assert result.ok is True


def test_missing_selector_fails():
    svc = UISelectorAmbiguityDetector()
    result = svc.detect({"type": "fill", "selector": None})
    assert result.ok is False
    assert result.confidence == "none"


def test_data_testid_stable_selector_passes():
    svc = UISelectorAmbiguityDetector()
    result = svc.detect({"type": "click", "selector": "[data-testid='formula-tab']"})
    assert result.ok is True
    assert result.confidence == "high"


def test_text_based_selector_is_ambiguous():
    svc = UISelectorAmbiguityDetector()
    result = svc.detect({"type": "click", "selector": "button:text('Submit')"})
    assert result.ok is False
    assert result.confidence == "low"


def test_aria_label_selector_is_acceptable():
    svc = UISelectorAmbiguityDetector()
    result = svc.detect({"type": "click", "selector": "[aria-label='Open order SO-VALID']"})
    assert result.ok is True
    assert result.confidence == "medium"


def test_name_selector_is_acceptable():
    svc = UISelectorAmbiguityDetector()
    result = svc.detect({"type": "fill", "selector": "[name='q']"})
    assert result.ok is True


def test_unknown_data_testid_still_accepted():
    svc = UISelectorAmbiguityDetector()
    result = svc.detect({"type": "click", "selector": "[data-testid='some-new-button']"})
    assert result.ok is True
    assert result.confidence == "high"
    assert "unrecognized" in result.detail
