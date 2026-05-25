"""Sprint 37 — Agent Candidate Activation Request UI smoke tests."""
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


def test_sprint_37_card_present():
    assert "Sprint 37" in _html()


def test_explicit_activation_request_heading():
    assert "Explicit Activation Request" in _html()


def test_button_activation_eligibility():
    assert 'id="activationEligibility"' in _html()


def test_button_create_activation_request():
    assert 'id="createActivationRequest"' in _html()


def test_button_activation_request_status():
    assert 'id="activationRequestStatus"' in _html()


def test_button_final_activation_gate():
    assert 'id="finalActivationGate"' in _html()


def test_button_activation_request_audit():
    assert 'id="activationRequestAudit"' in _html()


def test_output_element_present():
    assert 'id="activationRequestOutput"' in _html()


def test_no_activation_text():
    html = _html()
    assert "no activation" in html.lower() or "No activation" in html


def test_activation_request_id_saved_in_state():
    assert "cabState.activationRequestId" in _html()
