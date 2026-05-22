from __future__ import annotations

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_demo_has_skill_versioning_section():
    r = client.get("/demo")
    assert r.status_code == 200
    body = r.text
    assert "Skill Versioning" in body
    assert "Sprint 23" in body


def test_demo_has_lifecycle_buttons():
    r = client.get("/demo")
    body = r.text
    assert 'data-testid="demo-sv-create"' in body
    assert 'data-testid="demo-sv-readiness"' in body
    assert 'data-testid="demo-sv-promote"' in body
    assert 'data-testid="demo-sv-approve"' in body
    assert 'data-testid="demo-sv-activate"' in body
    assert 'data-testid="demo-sv-audit"' in body


def test_demo_has_rollback_buttons():
    r = client.get("/demo")
    body = r.text
    assert 'data-testid="demo-sv-rollback-plan"' in body
    assert 'data-testid="demo-sv-rollback-execute"' in body
    assert 'data-testid="demo-sv-compare"' in body


def test_demo_mentions_immutable():
    r = client.get("/demo")
    assert "immutable" in r.text.lower()


def test_demo_mentions_rollback_lifecycle_switch():
    r = client.get("/demo")
    body = r.text
    assert "lifecycle switch" in body.lower() or "rollback" in body.lower()


def test_demo_mentions_no_automatic_execution():
    r = client.get("/demo")
    body = r.text
    assert "automatic execution" in body.lower() or "No automatic" in body
