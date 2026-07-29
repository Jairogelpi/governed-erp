from __future__ import annotations

from erpguard.recording_pipeline.ui_record_identity_verifier import UIRecordIdentityVerifier


def test_navigate_step_does_not_require_record():
    svc = UIRecordIdentityVerifier()
    result = svc.verify({"type": "navigate"}, {"current_order": None})
    assert result.ok is True


def test_fill_step_passes_without_order():
    svc = UIRecordIdentityVerifier()
    result = svc.verify({"type": "fill"}, {"current_order": None})
    assert result.ok is True


def test_guard_step_fails_without_order():
    svc = UIRecordIdentityVerifier()
    result = svc.verify({"type": "guard", "guard": "formula_guard"}, {"current_order": None})
    assert result.ok is False
    assert "no_order" in result.detail


def test_guard_step_passes_with_known_order():
    svc = UIRecordIdentityVerifier()
    result = svc.verify({"type": "guard"}, {"current_order": "SO-VALID"})
    assert result.ok is True
    assert result.record_ref == "SO-VALID"


def test_unknown_order_reference_fails():
    svc = UIRecordIdentityVerifier()
    result = svc.verify({"type": "guard"}, {"current_order": "SO-NONEXISTENT"})
    assert result.ok is False
    assert result.record_ref == "SO-NONEXISTENT"


def test_click_with_unknown_order_fails():
    svc = UIRecordIdentityVerifier()
    result = svc.verify({"type": "click"}, {"current_order": "SO-UNKNOWN"})
    assert result.ok is False
