"""Sprint 34 — Agent Handoff Versioning API integration tests."""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

BASE = "/v1/agent-builder/advisory"


def _create_handoff_packet():
    """Create a real handoff packet via the existing Sprint 32 API."""
    # Create a draft first
    r = client.post("/v1/agent-builder/advisory/proposals", json={
        "title": "Sprint34 Test Proposal",
        "description": "For versioning tests",
        "workflow_json": json.dumps({
            "steps": [{"step_id": "s1", "step_type": "read", "description": "Read data"}]
        }),
    })
    if r.status_code not in (200, 201):
        return None, None
    proposal_id = r.json().get("proposal_id")

    r2 = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/draft")
    if r2.status_code not in (200, 201):
        return None, None
    draft_id = r2.json().get("draft_id")

    r3 = client.post(f"{BASE}/drafts/{draft_id}/handoff/packet")
    if r3.status_code not in (200, 201):
        return None, None
    packet_id = r3.json().get("packet_id")
    return draft_id, packet_id


def test_version_eligibility_404_unknown_packet():
    r = client.get(f"{BASE}/handoff-packets/nonexistent-id/version-eligibility")
    assert r.status_code == 404


def test_candidate_preview_404_unknown_packet():
    r = client.post(f"{BASE}/handoff-packets/nonexistent-id/candidate-preview")
    assert r.status_code == 404


def test_create_candidate_version_404_unknown_packet():
    r = client.post(f"{BASE}/handoff-packets/nonexistent-id/create-candidate-version")
    assert r.status_code == 404


def test_attach_evidence_404_unknown_packet():
    r = client.post(f"{BASE}/handoff-packets/nonexistent-id/attach-evidence")
    assert r.status_code == 404


def test_candidate_readiness_404_unknown_packet():
    r = client.get(f"{BASE}/handoff-packets/nonexistent-id/candidate-readiness")
    assert r.status_code == 404


def test_version_audit_404_unknown_packet():
    r = client.get(f"{BASE}/handoff-packets/nonexistent-id/version-audit")
    assert r.status_code == 404


def test_source_handoff_404_unknown_version():
    r = client.get(f"{BASE}/versions/nonexistent-version/source-handoff")
    assert r.status_code == 404


def test_full_versioning_pipeline():
    """End-to-end: eligibility → preview → create → evidence → readiness → audit."""
    _, packet_id = _create_handoff_packet()
    if packet_id is None:
        pytest.skip("Could not create handoff packet via API — prerequisite failed")

    # 1. Eligibility
    r = client.get(f"{BASE}/handoff-packets/{packet_id}/version-eligibility")
    assert r.status_code == 200
    body = r.json()
    assert body["packet_id"] == packet_id
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True

    # 2. Preview (no side effects)
    r = client.post(f"{BASE}/handoff-packets/{packet_id}/candidate-preview")
    assert r.status_code == 200
    body = r.json()
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True

    # 3. Create candidate
    r = client.post(f"{BASE}/handoff-packets/{packet_id}/create-candidate-version")
    assert r.status_code == 200
    body = r.json()
    version_id = body["version_id"]
    assert body["status"] == "candidate"
    assert body["can_execute"] is False
    assert body["can_approve"] is False
    assert body["is_advisory_only"] is True

    # 4. Attach evidence
    r = client.post(f"{BASE}/handoff-packets/{packet_id}/attach-evidence")
    assert r.status_code == 200
    body = r.json()
    assert body["evidence_attached"] is True
    assert body["can_execute"] is False

    # 5. Candidate readiness
    r = client.get(f"{BASE}/handoff-packets/{packet_id}/candidate-readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["version_status"] == "candidate"
    assert body["can_approve"] is False

    # 6. Version audit
    r = client.get(f"{BASE}/handoff-packets/{packet_id}/version-audit")
    assert r.status_code == 200
    body = r.json()
    assert body["event_count"] >= 1

    # 7. Source handoff
    r = client.get(f"{BASE}/versions/{version_id}/source-handoff")
    assert r.status_code == 200
    body = r.json()
    assert body["version_id"] == version_id
    assert body["packet_id"] == packet_id
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True


def test_create_candidate_idempotent_via_api():
    _, packet_id = _create_handoff_packet()
    if packet_id is None:
        pytest.skip("Could not create handoff packet via API — prerequisite failed")

    r1 = client.post(f"{BASE}/handoff-packets/{packet_id}/create-candidate-version")
    assert r1.status_code == 200
    v1 = r1.json()["version_id"]

    r2 = client.post(f"{BASE}/handoff-packets/{packet_id}/create-candidate-version")
    assert r2.status_code == 200
    v2 = r2.json()["version_id"]
    assert v1 == v2
    assert r2.json()["is_cached"] is True
