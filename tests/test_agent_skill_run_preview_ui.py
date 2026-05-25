"""Sprint 39 — Agent Skill Run Preview UI smoke tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app


@pytest.fixture()
def client():
    with TestClient(app) as c:
        yield c


def test_demo_dashboard_loads(client):
    r = client.get("/demo")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]


def test_sprint39_card_present(client):
    r = client.get("/demo")
    html = r.text
    assert "run-preview" in html.lower() or "Run Preview" in html


def test_run_preview_eligibility_button_present(client):
    r = client.get("/demo")
    assert "runPreviewEligibility" in r.text


def test_build_run_plan_button_present(client):
    r = client.get("/demo")
    assert "buildRunPlan" in r.text


def test_execution_gate_button_present(client):
    r = client.get("/demo")
    assert "executionGate" in r.text


def test_run_preview_button_present(client):
    r = client.get("/demo")
    assert "runPreview" in r.text


def test_run_preview_audit_button_present(client):
    r = client.get("/demo")
    assert "runPreviewAudit" in r.text


def test_run_preview_output_element_present(client):
    r = client.get("/demo")
    assert "runPreviewOutput" in r.text


def test_no_execution_language_present(client):
    r = client.get("/demo")
    html = r.text
    assert (
        "advisory" in html.lower()
        or "no execution" in html.lower()
        or "will_execute" in html.lower()
        or "preview" in html.lower()
    )


def test_dashboard_contains_previous_sprint_cards(client):
    r = client.get("/demo")
    html = r.text
    assert "activationOutput" in html
    assert "cabState" in html
