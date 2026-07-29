from __future__ import annotations

from erpguard.recording_pipeline.ui_modal_error_detector import UIModalErrorDetector

_BASE = "http://localhost:8000/fake-erp"


def test_navigate_step_skips_modal_check():
    svc = UIModalErrorDetector()
    result = svc.detect({"current_url": _BASE}, {"type": "navigate"})
    assert result.ok is True


def test_no_modal_in_clean_state():
    svc = UIModalErrorDetector()
    result = svc.detect({"current_url": _BASE + "/sales/orders", "current_order": "SO-VALID"}, {"type": "fill"})
    assert result.ok is True
    assert result.blocking is False


def test_explicit_error_state_blocks():
    svc = UIModalErrorDetector()
    result = svc.detect({"current_url": _BASE, "error_state": "validation_failed"}, {"type": "click"})
    assert result.ok is False
    assert result.blocking is True
    assert result.modal_type == "error"


def test_so_empty_lines_blocks_guard():
    svc = UIModalErrorDetector()
    result = svc.detect({"current_order": "SO-EMPTY-LINES"}, {"type": "guard"})
    assert result.ok is False
    assert result.blocking is True
    assert "order_has_no_lines" in result.detail


def test_so_empty_lines_does_not_block_fill():
    svc = UIModalErrorDetector()
    result = svc.detect({"current_order": "SO-EMPTY-LINES"}, {"type": "fill"})
    assert result.ok is True


def test_so_valid_does_not_block_guard():
    svc = UIModalErrorDetector()
    result = svc.detect({"current_order": "SO-VALID"}, {"type": "guard"})
    assert result.ok is True
