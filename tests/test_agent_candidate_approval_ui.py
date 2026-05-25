"""Sprint 35 — Agent Candidate Approval UI smoke tests."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def _html():
    r = client.get("/demo")
    assert r.status_code == 200
    return r.text


def test_dashboard_loads():
    r = client.get("/demo")
    assert r.status_code == 200


def test_approval_bridge_card_present():
    assert "Candidate Approval Bridge" in _html()


def test_sprint_35_label():
    assert "Sprint 35" in _html()


def test_button_promotion_readiness():
    assert 'id="promotionReadiness"' in _html()


def test_button_evidence_completeness():
    assert 'id="evidenceCompleteness"' in _html()


def test_button_risk_summary():
    assert 'id="riskSummary"' in _html()


def test_button_approval_packet():
    assert 'id="approvalPacket"' in _html()


def test_button_approval_request():
    assert 'id="approvalRequest"' in _html()


def test_button_approval_audit():
    assert 'id="approvalAudit"' in _html()


def test_output_element_present():
    assert 'id="approvalOutput"' in _html()


def test_approval_packet_id_saved():
    """approvalPacket handler must save cabState.approvalPacketId."""
    assert "cabState.approvalPacketId" in _html()


def test_advisory_safety_text_present():
    html = _html()
    assert "advisory" in html.lower() or "no auto-approve" in html.lower()
