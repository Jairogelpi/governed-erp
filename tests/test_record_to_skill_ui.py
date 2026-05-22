from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_contains_sprint20_section():
    r = client.get("/demo")
    assert r.status_code == 200
    body = r.text
    assert "Record-to-Skill End-to-End Loop" in body
    assert "Sprint 20" in body


def test_demo_dashboard_has_record_to_skill_buttons():
    r = client.get("/demo")
    body = r.text
    assert "r2sCreateSession" in body
    assert "r2sCaptureEvents" in body
    assert "r2sFinishSession" in body
    assert "r2sGenerateDraft" in body
    assert "r2sCompileSkill" in body
    assert "r2sReplay" in body
    assert "r2sAudit" in body
    assert "r2sReport" in body


def test_demo_dashboard_explains_no_llm_at_replay():
    r = client.get("/demo")
    body = r.text
    assert "No LLM at replay time" in body or "llm" in body.lower()


def test_demo_dashboard_mentions_deterministic():
    r = client.get("/demo")
    body = r.text
    assert "deterministic" in body.lower()


def test_demo_dashboard_mentions_audit():
    r = client.get("/demo")
    body = r.text
    assert "Audit" in body or "audit" in body
