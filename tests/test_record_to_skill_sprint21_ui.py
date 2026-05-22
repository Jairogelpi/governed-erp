from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_has_sprint21_section():
    r = client.get("/demo")
    assert r.status_code == 200
    body = r.text
    assert "Sprint 21" in body
    assert "Real Browser Recorder" in body


def test_demo_dashboard_has_open_recorder_button():
    r = client.get("/demo")
    body = r.text
    assert "r2sOpenRecorder" in body
    assert "demo-r2s-open-recorder" in body


def test_demo_dashboard_has_inject_demo_events_button():
    r = client.get("/demo")
    body = r.text
    assert "r2sCaptureEvents" in body
    assert "Inject demo events" in body


def test_demo_dashboard_mentions_overlay():
    r = client.get("/demo")
    body = r.text
    assert "overlay" in body.lower()


def test_demo_dashboard_mentions_fake_erp_recorder():
    r = client.get("/demo")
    body = r.text
    assert "fake-erp" in body.lower() or "Fake ERP" in body


def test_demo_dashboard_explains_stop():
    r = client.get("/demo")
    body = r.text
    assert "Stop" in body


def test_demo_recorder_flow_buttons_have_data_testids():
    r = client.get("/demo")
    body = r.text
    assert 'data-testid="demo-r2s-create-session"' in body
    assert 'data-testid="demo-r2s-open-recorder"' in body
    assert 'data-testid="demo-r2s-generate-draft"' in body
    assert 'data-testid="demo-r2s-compile-skill"' in body
    assert 'data-testid="demo-r2s-replay"' in body
    assert 'data-testid="demo-r2s-audit"' in body
    assert 'data-testid="demo-r2s-report"' in body
