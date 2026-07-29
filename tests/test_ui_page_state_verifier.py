from __future__ import annotations

from erpguard.recording_pipeline.ui_page_state_verifier import UIPageStateVerifier

_BASE = "http://localhost:8000/fake-erp"


def test_navigate_step_always_passes():
    svc = UIPageStateVerifier()
    result = svc.verify({"type": "navigate", "url": _BASE + "/sales/orders"}, {"current_url": ""})
    assert result.ok is True


def test_fill_on_fake_erp_passes():
    svc = UIPageStateVerifier()
    result = svc.verify({"type": "fill", "selector": "[data-testid='order-search']"}, {"current_url": _BASE + "/sales/orders"})
    assert result.ok is True


def test_fill_with_no_url_fails():
    svc = UIPageStateVerifier()
    result = svc.verify({"type": "fill"}, {"current_url": ""})
    assert result.ok is False
    assert "no_current_url" in result.detail


def test_fill_on_non_fake_erp_fails():
    svc = UIPageStateVerifier()
    result = svc.verify({"type": "fill"}, {"current_url": "http://production-odoo.example.com/orders"})
    assert result.ok is False
    assert "not_on_fake_erp" in result.detail


def test_click_on_correct_page_passes():
    svc = UIPageStateVerifier()
    url = _BASE + "/sales/orders/SO-VALID"
    result = svc.verify({"type": "click", "url": url}, {"current_url": url})
    assert result.ok is True
