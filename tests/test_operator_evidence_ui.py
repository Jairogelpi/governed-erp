from __future__ import annotations

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_demo_dashboard_has_evidence_pack_section():
    r = client.get("/demo")
    assert r.status_code == 200
    html = r.text
    assert "Operator Evidence Pack" in html
    assert "demo-ep-seed" in html
    assert "demo-ep-assemble" in html
    assert "demo-ep-runbook" in html


def test_demo_dashboard_has_ep_buttons():
    r = client.get("/demo")
    html = r.text
    assert "demo-ep-get-pack" in html
    assert "demo-ep-safety" in html
    assert "demo-ep-final-report" in html


def test_demo_dashboard_has_ep_outputs():
    r = client.get("/demo")
    html = r.text
    assert "epSeedOutput" in html
    assert "epAssembleOutput" in html
    assert "epRunbookOutput" in html
    assert "epSafetyOutput" in html
    assert "epFinalOutput" in html


def test_demo_dashboard_ep_js_handlers():
    r = client.get("/demo")
    html = r.text
    assert "epSeed" in html
    assert "epAssemble" in html
    assert "epRunbook" in html
    assert "/v1/operator/evidence-packs" in html
    assert "/v1/operator/demo-runbook" in html


def test_demo_dashboard_ep_safety_note():
    r = client.get("/demo")
    html = r.text
    assert "Fake ERP only" in html
    assert "No LLM replay" in html or "No background scheduler" in html


def test_demo_dashboard_sprint_26_label():
    r = client.get("/demo")
    html = r.text
    assert "Sprint 26" in html
