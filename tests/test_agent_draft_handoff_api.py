"""Sprint 32 — API integration tests for the agent draft handoff endpoints."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def _make_draft() -> tuple[str, str]:
    r = client.post(
        "/v1/agent-builder/advisory/sessions",
        json={"created_by": {"type": "test"}},
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    r = client.post(
        f"/v1/agent-builder/advisory/sessions/{session_id}/propose",
        json={"request_text": "Read all draft sales orders and generate a daily summary report"},
    )
    assert r.status_code == 200, r.text
    proposal_id = r.json()["proposal_id"]

    r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    assert r.status_code == 200, r.text
    draft_id = r.json()["draft_id"]

    return draft_id, proposal_id


def _run_bridge(draft_id: str, proposal_id: str) -> None:
    """Run all Sprint 31 bridge steps to make the draft ready."""
    state_r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarifications")
    questions = state_r.json().get("questions", [])
    if questions:
        answers = [{"question_id": q["question_id"], "answer_text": "test answer"} for q in questions]
        client.post(
            f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarifications/answers",
            json={"answers": answers},
        )
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarification-status")
    mappings_total = r.json().get("mappings_total", 0)
    for i in range(mappings_total):
        client.post(
            f"/v1/agent-builder/advisory/proposals/{proposal_id}/mappings/mapping_{i}/confirm",
            json={"reason": "test"},
        )
    client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/review")
    client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/validate")
    client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/compile-plan")


# ── 404 tests ────────────────────────────────────────────────────────────────

def test_proof_plan_404():
    r = client.post("/v1/agent-builder/advisory/drafts/nonexistent/handoff/proof-plan")
    assert r.status_code == 404


def test_evidence_404():
    r = client.get("/v1/agent-builder/advisory/drafts/nonexistent/handoff/evidence")
    assert r.status_code == 404


def test_readiness_404():
    r = client.get("/v1/agent-builder/advisory/drafts/nonexistent/handoff/readiness")
    assert r.status_code == 404


def test_packet_404():
    r = client.post("/v1/agent-builder/advisory/drafts/nonexistent/handoff/packet")
    assert r.status_code == 404


def test_audit_404():
    r = client.get("/v1/agent-builder/advisory/drafts/nonexistent/handoff/audit")
    assert r.status_code == 404


# ── 200 tests ────────────────────────────────────────────────────────────────

def test_proof_plan_200():
    draft_id, _ = _make_draft()
    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/proof-plan")
    assert r.status_code == 200
    body = r.json()
    assert body["plan_generated"] is True
    assert body["can_execute"] is False
    assert body["proof_is_plan_only"] is True
    assert body["scenario_count"] > 0


def test_evidence_200():
    draft_id, _ = _make_draft()
    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/evidence")
    assert r.status_code == 200
    body = r.json()
    assert "evidence_items" in body
    assert body["can_execute"] is False


def test_readiness_200():
    draft_id, _ = _make_draft()
    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/readiness")
    assert r.status_code == 200
    body = r.json()
    assert "ready" in body
    assert body["can_execute"] is False
    assert body["can_approve"] is False


def test_packet_200():
    draft_id, _ = _make_draft()
    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/packet")
    assert r.status_code == 200
    body = r.json()
    assert "packet_id" in body
    assert body["can_execute"] is False
    assert body["can_approve"] is False
    assert body["status"] == "pending_human_review"


def test_audit_200():
    draft_id, _ = _make_draft()
    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/audit")
    assert r.status_code == 200
    body = r.json()
    assert "event_count" in body
    assert body["can_execute"] is False


def test_packet_idempotent():
    draft_id, _ = _make_draft()
    r1 = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/packet")
    r2 = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/packet")
    assert r1.json()["packet_id"] == r2.json()["packet_id"]
    assert r2.json()["is_cached"] is True


def test_full_handoff_pipeline():
    draft_id, proposal_id = _make_draft()
    _run_bridge(draft_id, proposal_id)

    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/proof-plan")
    assert r.json()["plan_generated"] is True

    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/evidence")
    assert "evidence_items" in r.json()

    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/readiness")
    body = r.json()
    assert body["ready"] is True
    assert body["overall_score"] == 100

    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/packet")
    assert r.json()["ready_for_review"] is True

    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/audit")
    assert r.json()["event_count"] >= 3


def test_no_execution_flag_all_endpoints():
    draft_id, _ = _make_draft()
    endpoints = [
        ("POST", f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/proof-plan"),
        ("GET", f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/evidence"),
        ("GET", f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/readiness"),
        ("POST", f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/packet"),
        ("GET", f"/v1/agent-builder/advisory/drafts/{draft_id}/handoff/audit"),
    ]
    for method, url in endpoints:
        r = client.get(url) if method == "GET" else client.post(url)
        assert r.status_code == 200, f"Expected 200 for {url}, got {r.status_code}"
        body = r.json()
        assert body.get("can_execute") is False, f"can_execute not False for {url}"
        if "can_approve" in body:
            assert body["can_approve"] is False, f"can_approve not False for {url}"
