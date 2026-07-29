from __future__ import annotations

from erpguard.release_ops.ui_recorder_script import (
    build_recorder_script,
    selector_priority_attrs,
    secret_field_names,
)


def test_build_recorder_script_contains_rsid():
    script = build_recorder_script("ui_session_abc123")
    assert "ui_session_abc123" in script


def test_build_recorder_script_has_correct_events_endpoint():
    script = build_recorder_script("ui_session_abc123")
    # endpoint is built at runtime: apiBase + "/v1/record-to-skill/sessions/" + rsid + "/events"
    assert "/v1/record-to-skill/sessions/" in script
    assert '"events"' in script or "/events" in script
    assert "ui_session_abc123" in script


def test_build_recorder_script_has_finish_endpoint():
    script = build_recorder_script("ui_session_abc123")
    # finish endpoint is built at runtime
    assert "/v1/record-to-skill/sessions/" in script
    assert "finish" in script
    assert "ui_session_abc123" in script


def test_build_recorder_script_has_overlay():
    script = build_recorder_script("ui_session_abc123")
    assert "erpguard-recorder-overlay" in script
    assert "erpguard-recorder-count" in script
    assert "erpguard-recorder-stop" in script


def test_build_recorder_script_has_selector_priority_attrs():
    script = build_recorder_script("ui_session_abc123")
    for attr in selector_priority_attrs():
        assert attr in script


def test_build_recorder_script_has_redaction():
    script = build_recorder_script("ui_session_abc123")
    assert "[REDACTED]" in script
    assert "password" in script


def test_build_recorder_script_captures_click():
    script = build_recorder_script("ui_session_abc123")
    assert "click" in script
    assert "addEventListener" in script


def test_build_recorder_script_captures_change():
    script = build_recorder_script("ui_session_abc123")
    assert "change" in script


def test_build_recorder_script_captures_page_load():
    script = build_recorder_script("ui_session_abc123")
    assert "page_load" in script


def test_build_recorder_script_has_navigate_capture():
    script = build_recorder_script("ui_session_abc123")
    assert "navigate" in script
    assert "pushState" in script


def test_build_recorder_script_with_api_base():
    script = build_recorder_script("ui_session_xyz", api_base="http://localhost:9000")
    assert "http://localhost:9000" in script


def test_build_recorder_script_wrapped_in_script_tag():
    script = build_recorder_script("ui_session_abc123")
    assert "<script" in script
    assert "</script>" in script


def test_selector_priority_attrs_order():
    attrs = selector_priority_attrs()
    assert attrs[0] == "data-testid"
    assert "aria-label" in attrs
    assert "name" in attrs
    assert "placeholder" in attrs


def test_secret_field_names_contains_password():
    names = secret_field_names()
    assert "password" in names
    assert "token" in names
    assert "secret" in names
