from __future__ import annotations

from erpguard.product.ui_recording_normalizer import UIRecordingNormalizerService


def _make_raw_events(specs: list[dict]) -> list[dict]:
    return [{"event_type": s.get("event_type", "click"), "url": s.get("url"), "selector": s.get("selector"), "element_text": s.get("element_text"), "element_label": s.get("element_label"), "input_value": s.get("input_value"), "metadata": {}} for s in specs]


def test_normalize_basic_flow():
    svc = UIRecordingNormalizerService()
    raw = _make_raw_events([
        {"event_type": "navigate", "url": "http://localhost:8000/fake-erp/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
        {"event_type": "click", "selector": "[data-testid='open-order-SO-VALID']"},
    ])
    result = svc.normalize("sess_test", raw)
    assert result.event_count == 3
    assert result.diagnostics == []
    assert result.events[0].event_type == "navigate"
    assert result.events[1].event_type == "fill"


def test_normalize_drops_mousemove():
    svc = UIRecordingNormalizerService()
    raw = _make_raw_events([
        {"event_type": "mousemove"},
        {"event_type": "navigate", "url": "http://localhost:8000/fake-erp/orders"},
        {"event_type": "scroll"},
    ])
    result = svc.normalize("sess_test", raw)
    assert result.event_count == 1
    assert result.events[0].event_type == "navigate"


def test_normalize_deduplicates_repeated_clicks():
    svc = UIRecordingNormalizerService()
    raw = _make_raw_events([
        {"event_type": "click", "selector": "[data-testid='btn']"},
        {"event_type": "click", "selector": "[data-testid='btn']"},
    ])
    result = svc.normalize("sess_test", raw)
    assert result.event_count == 1


def test_normalize_empty_events():
    svc = UIRecordingNormalizerService()
    result = svc.normalize("sess_test", [])
    assert result.event_count == 0
    assert "no_events_after_normalization" in result.diagnostics


def test_normalized_events_are_reindexed():
    svc = UIRecordingNormalizerService()
    raw = _make_raw_events([
        {"event_type": "mousemove"},
        {"event_type": "navigate", "url": "http://localhost:8000/fake-erp/orders"},
        {"event_type": "scroll"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
    ])
    result = svc.normalize("sess_test", raw)
    indices = [ev.event_index for ev in result.events]
    assert indices == list(range(len(indices)))
