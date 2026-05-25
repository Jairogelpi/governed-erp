"""Sprint 34 — Agent Handoff Versioning UI smoke tests."""
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


def test_version_handoff_card_present():
    html = _html()
    assert "Version Handoff" in html


def test_button_version_eligibility():
    assert 'id="versionEligibility"' in _html()


def test_button_candidate_preview():
    assert 'id="candidatePreview"' in _html()


def test_button_create_candidate_version():
    assert 'id="createCandidateVersion"' in _html()


def test_button_attach_evidence():
    assert 'id="attachEvidence"' in _html()


def test_button_candidate_readiness():
    assert 'id="candidateReadiness"' in _html()


def test_button_version_audit():
    assert 'id="versionAudit"' in _html()


def test_output_element_present():
    assert 'id="versionOutput"' in _html()


def test_sprint_34_label():
    html = _html()
    assert "Sprint 34" in html or "34" in html


def test_cab_state_packet_id_saved():
    """handoffPacket handler must save cabState.packetId."""
    html = _html()
    assert "cabState.packetId" in html


def test_safety_note_or_advisory_text():
    html = _html()
    assert "advisory" in html.lower() or "candidate only" in html.lower() or "is_advisory_only" in html.lower()
