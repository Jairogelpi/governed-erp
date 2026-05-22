from __future__ import annotations

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_demo_has_verified_replay_section():
    r = client.get("/demo")
    assert r.status_code == 200
    body = r.text
    assert "Verified UI Replay" in body
    assert "Sprint 22" in body


def test_demo_has_verified_replay_buttons():
    r = client.get("/demo")
    body = r.text
    assert 'data-testid="demo-verif-replay"' in body
    assert 'data-testid="demo-verif-verification"' in body
    assert 'data-testid="demo-verif-failures"' in body
    assert 'data-testid="demo-verif-robust-report"' in body


def test_demo_mentions_fail_closed():
    r = client.get("/demo")
    body = r.text
    assert "fail closed" in body.lower() or "Fail closed" in body


def test_demo_mentions_no_automatic_repair():
    r = client.get("/demo")
    body = r.text
    assert "automatic repair" in body.lower() or "repair" in body.lower()


def test_demo_mentions_no_coordinate_automation():
    r = client.get("/demo")
    body = r.text
    assert "coordinate" in body.lower()


def test_demo_has_recovery_suggestion_concept():
    r = client.get("/demo")
    body = r.text
    assert "recovery" in body.lower()
