"""Sprint 31 — API integration tests for the agent draft bridge endpoints."""
from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def _make_draft() -> tuple[str, str]:
    """Create a full advisory session + proposal + draft via API. Returns (draft_id, proposal_id)."""
    r = client.post(
        "/v1/agent-builder/advisory/sessions",
        json={"created_by": {"type": "test"}},
    )
    assert r.status_code == 200, r.text
    session_id = r.json()["session_id"]

    r = client.post(
        f"/v1/agent-builder/advisory/sessions/{session_id}/propose",
        json={"request_text": "Read all draft sales orders and send a daily report every morning at 8 AM"},
    )
    assert r.status_code == 200, r.text
    proposal_id = r.json()["proposal_id"]

    r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    assert r.status_code == 200, r.text
    draft_id = r.json()["draft_id"]

    return draft_id, proposal_id


def _answer_all_clarifications(proposal_id: str) -> None:
    """Answer all clarification questions and confirm entity mappings so the gate passes."""
    state_r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarifications")
    questions = state_r.json().get("questions", [])
    if questions:
        answers = [{"question_id": q["question_id"], "answer_text": "test answer"} for q in questions]
        client.post(
            f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarifications/answers",
            json={"answers": answers},
        )

    # Confirm all entity mappings so mappings_pct >= 50%
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarification-status")
    mappings_total = r.json().get("mappings_total", 0)
    if mappings_total > 0:
        for i in range(mappings_total):
            client.post(
                f"/v1/agent-builder/advisory/proposals/{proposal_id}/mappings/mapping_{i}/confirm",
                json={"reason": "test confirm"},
            )


def test_eligibility_404():
    r = client.post("/v1/agent-builder/advisory/drafts/nonexistent/bridge/eligibility")
    assert r.status_code == 404


def test_eligibility_200():
    draft_id, _ = _make_draft()
    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/eligibility")
    assert r.status_code == 200
    body = r.json()
    assert body["eligible"] is True
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True


def test_clarification_gate_200():
    draft_id, _ = _make_draft()
    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/clarification-gate")
    assert r.status_code == 200
    body = r.json()
    assert "gate_passed" in body
    assert body["can_execute"] is False


def test_review_bridge_200():
    draft_id, _ = _make_draft()
    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/review")
    assert r.status_code == 200
    body = r.json()
    assert body["bridged"] is True
    assert body["review_id"] is not None
    assert body["can_execute"] is False


def test_validate_bridge_200():
    draft_id, _ = _make_draft()
    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/validate")
    assert r.status_code == 200
    body = r.json()
    assert "validation_passed" in body
    assert body["can_execute"] is False


def test_compile_plan_200():
    draft_id, _ = _make_draft()
    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/compile-plan")
    assert r.status_code == 200
    body = r.json()
    assert body["plan_generated"] is True
    assert len(body["plan_steps"]) == 6
    assert body["can_execute"] is False
    assert "advisory only" in body["safety_note"].lower()


def test_bridge_report_200():
    draft_id, _ = _make_draft()
    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/report")
    assert r.status_code == 200
    body = r.json()
    assert "overall_status" in body
    assert body["can_execute"] is False


def test_bridge_audit_200():
    draft_id, _ = _make_draft()
    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/audit")
    assert r.status_code == 200
    body = r.json()
    assert "event_count" in body
    assert body["can_execute"] is False


def test_bridge_report_404():
    r = client.get("/v1/agent-builder/advisory/drafts/nonexistent/bridge/report")
    assert r.status_code == 404


def test_bridge_validate_404():
    r = client.post("/v1/agent-builder/advisory/drafts/nonexistent/bridge/validate")
    assert r.status_code == 404


def test_review_idempotent():
    draft_id, _ = _make_draft()
    r1 = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/review")
    r2 = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/review")
    assert r1.json()["review_id"] == r2.json()["review_id"]


def test_full_bridge_pipeline():
    draft_id, proposal_id = _make_draft()
    _answer_all_clarifications(proposal_id)

    client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/review")
    client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/validate")
    client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/compile-plan")

    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/report")
    body = r.json()
    assert body["overall_status"] == "complete"
    assert "human review" in body["next_action"].lower()

    r2 = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/audit")
    assert r2.json()["event_count"] >= 3


def test_no_execution_flag_across_all_endpoints():
    draft_id, _ = _make_draft()
    endpoints = [
        ("POST", f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/eligibility"),
        ("POST", f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/clarification-gate"),
        ("POST", f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/review"),
        ("POST", f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/validate"),
        ("POST", f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/compile-plan"),
        ("GET", f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/report"),
        ("GET", f"/v1/agent-builder/advisory/drafts/{draft_id}/bridge/audit"),
    ]
    for method, url in endpoints:
        r = client.get(url) if method == "GET" else client.post(url)
        assert r.status_code == 200, f"Expected 200 for {url}, got {r.status_code}"
        assert r.json().get("can_execute") is False, f"can_execute not False for {url}"
