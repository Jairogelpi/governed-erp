"""Sprint 36 — Agent Candidate Decision UI smoke tests."""
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


def test_human_decision_card_present():
    assert "Human Decision" in _html()


def test_sprint_36_label():
    assert "Sprint 36" in _html()


def test_button_submit_decision():
    assert 'id="submitDecision"' in _html()


def test_button_decision_history():
    assert 'id="decisionHistory"' in _html()


def test_button_activation_gate():
    assert 'id="activationGate"' in _html()


def test_button_governance_summary():
    assert 'id="governanceSummary"' in _html()


def test_button_decision_audit():
    assert 'id="decisionAudit"' in _html()


def test_output_element_present():
    assert 'id="decisionOutput"' in _html()


def test_decision_id_saved_in_state():
    assert "cabState.decisionId" in _html()


def test_no_auto_activation_text():
    html = _html()
    assert "no automatic activation" in html.lower() or "No automatic activation" in html
