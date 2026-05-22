from __future__ import annotations

from erpguard.product.ui_recording_session import UIRecordingSessionService


def test_create_and_get_session():
    svc = UIRecordingSessionService()
    result = svc.create_session(
        name="Test Session",
        description="Sprint 20 test",
        target_base_url="http://localhost:8000/fake-erp",
    )
    assert result.session_id.startswith("ui_session_")
    assert result.name == "Test Session"
    assert result.status == "recording"

    fetched = svc.get_session(result.session_id)
    assert fetched is not None
    assert fetched.session_id == result.session_id
    assert fetched.target_base_url == "http://localhost:8000/fake-erp"


def test_finish_session():
    svc = UIRecordingSessionService()
    s = svc.create_session(name="Finish Test", description=None, target_base_url="http://localhost:8000/fake-erp")
    finished = svc.finish_session(s.session_id)
    assert finished is not None
    assert finished.status == "finished"


def test_get_nonexistent_session_returns_none():
    svc = UIRecordingSessionService()
    assert svc.get_session("nonexistent_session_id") is None


def test_finish_nonexistent_session_returns_none():
    svc = UIRecordingSessionService()
    assert svc.finish_session("nonexistent_session_id") is None
