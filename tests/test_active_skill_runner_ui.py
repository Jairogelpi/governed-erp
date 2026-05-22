from __future__ import annotations

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_demo_has_active_runner_section():
    r = client.get("/demo")
    assert r.status_code == 200
    body = r.text
    assert "Active Skill Runner" in body
    assert "Sprint 24" in body


def test_demo_has_runner_buttons():
    r = client.get("/demo")
    body = r.text
    assert 'data-testid="demo-asr-run"' in body
    assert 'data-testid="demo-asr-get-run"' in body
    assert 'data-testid="demo-asr-events"' in body
    assert 'data-testid="demo-asr-report"' in body
    assert 'data-testid="demo-asr-list"' in body


def test_demo_mentions_active_only():
    r = client.get("/demo")
    body = r.text
    assert "active" in body.lower()


def test_demo_mentions_manual_only():
    r = client.get("/demo")
    body = r.text
    assert "Manual" in body or "manual" in body


def test_demo_mentions_no_scheduler():
    r = client.get("/demo")
    body = r.text
    assert "no scheduler" in body.lower() or "no background" in body.lower()
