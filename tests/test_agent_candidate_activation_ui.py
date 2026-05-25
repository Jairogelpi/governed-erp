"""Sprint 38 — Agent Candidate Activation UI smoke tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def _html():
    r = client.get("/demo")
    assert r.status_code == 200
    return r.text


def test_dashboard_loads():
    assert client.get("/demo").status_code == 200


def test_sprint_38_card_present():
    assert "Sprint 38" in _html()


def test_explicit_activation_heading():
    assert "Explicit Candidate Activation" in _html()


def test_button_activation_readiness():
    assert 'id="activationReadiness"' in _html()


def test_button_activate_candidate():
    assert 'id="activateCandidate"' in _html()


def test_button_activation_status():
    assert 'id="activationStatus"' in _html()


def test_button_activation_audit():
    assert 'id="activationAudit"' in _html()


def test_button_post_activation_summary():
    assert 'id="postActivationSummary"' in _html()


def test_output_element_present():
    assert 'id="activationOutput"' in _html()


def test_no_execution_text():
    html = _html()
    assert "no execution" in html.lower() or "No execution" in html
