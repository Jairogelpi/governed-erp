from __future__ import annotations

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_demo_has_scheduled_runs_section():
    r = client.get("/demo")
    assert r.status_code == 200
    body = r.text
    assert "Scheduled Skill Runs" in body
    assert "Sprint 25" in body


def test_demo_has_schedule_buttons():
    r = client.get("/demo")
    body = r.text
    assert 'data-testid="demo-sch-create"' in body
    assert 'data-testid="demo-sch-activate"' in body
    assert 'data-testid="demo-sch-pause"' in body
    assert 'data-testid="demo-sch-resume"' in body
    assert 'data-testid="demo-sch-disable"' in body
    assert 'data-testid="demo-sch-tick"' in body
    assert 'data-testid="demo-sch-events"' in body
    assert 'data-testid="demo-sch-queue"' in body


def test_demo_mentions_manual_tick_only():
    r = client.get("/demo")
    body = r.text
    assert "Manual tick only" in body or "manual tick only" in body.lower()


def test_demo_mentions_no_background_worker():
    r = client.get("/demo")
    body = r.text
    assert "background worker" in body.lower() or "no autonomous" in body.lower()


def test_demo_mentions_no_cron():
    r = client.get("/demo")
    body = r.text
    assert "cron" in body.lower()
