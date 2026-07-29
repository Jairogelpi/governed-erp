from __future__ import annotations

from erpguard.recording_pipeline.ui_recording_session import UIRecordingSessionService
from erpguard.recording_pipeline.ui_event_capture import UIEventCaptureService


def _make_session() -> str:
    svc = UIRecordingSessionService()
    return svc.create_session(
        name="Event Capture Test",
        description=None,
        target_base_url="http://localhost:8000/fake-erp",
    ).session_id


def test_capture_single_event():
    sid = _make_session()
    svc = UIEventCaptureService()
    ev = svc.capture_event(
        session_id=sid,
        event_type="navigate",
        url="http://localhost:8000/fake-erp/sales/orders",
    )
    assert ev.event_id.startswith("ui_ev_")
    assert ev.event_type == "navigate"
    assert ev.event_index == 0


def test_capture_multiple_events_indexed():
    sid = _make_session()
    svc = UIEventCaptureService()
    svc.capture_event(sid, "navigate", url="http://localhost:8000/fake-erp/orders")
    svc.capture_event(sid, "fill", selector="[data-testid='order-search']", input_value="SO-VALID")
    svc.capture_event(sid, "click", selector="[data-testid='open-order-SO-VALID']")

    events = svc.list_events(sid)
    assert len(events) == 3
    assert events[0].event_index == 0
    assert events[1].event_index == 1
    assert events[2].event_index == 2


def test_list_events_empty_session():
    sid = _make_session()
    svc = UIEventCaptureService()
    assert svc.list_events(sid) == []


def test_capture_event_with_metadata():
    sid = _make_session()
    svc = UIEventCaptureService()
    ev = svc.capture_event(
        sid, "fill",
        selector="[data-testid='order-search']",
        input_value="SO-VALID",
        metadata={"source": "test"},
    )
    assert ev.metadata == {"source": "test"}
