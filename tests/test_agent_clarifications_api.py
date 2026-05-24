from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def _make_eligible_proposal() -> tuple[str, str]:
    r = client.post(
        "/v1/agent-builder/advisory/sessions",
        json={"created_by": {"type": "test"}},
    )
    session_id = r.json()["session_id"]
    r = client.post(
        f"/v1/agent-builder/advisory/sessions/{session_id}/propose",
        json={"request_text": "List all draft sales orders and send a daily email report every morning"},
    )
    proposal_id = r.json()["proposal_id"]
    return session_id, proposal_id


def _make_draft(proposal_id: str) -> str:
    r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    return r.json()["draft_id"]


# ── GET /clarifications ───────────────────────────────────────────────────────

def test_get_clarifications_returns_questions():
    _, proposal_id = _make_eligible_proposal()
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarifications")
    assert r.status_code == 200
    body = r.json()
    assert "total_questions" in body
    assert "questions" in body
    assert body["is_advisory_only"] is True


def test_get_clarifications_unknown_proposal():
    r = client.get("/v1/agent-builder/advisory/proposals/missing_id/clarifications")
    assert r.status_code == 404


# ── POST /clarifications/answers ──────────────────────────────────────────────

def test_submit_answers_valid():
    _, proposal_id = _make_eligible_proposal()
    state_r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarifications")
    questions = state_r.json()["questions"]
    if not questions:
        return
    qid = questions[0]["question_id"]
    r = client.post(
        f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarifications/answers",
        json={"answers": [{"question_id": qid, "answer_text": "scheduled"}]},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["total_submitted"] >= 1
    assert body["is_advisory_only"] is True


def test_submit_answers_unknown_qid_skipped():
    _, proposal_id = _make_eligible_proposal()
    r = client.post(
        f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarifications/answers",
        json={"answers": [{"question_id": "q999", "answer_text": "something"}]},
    )
    assert r.status_code == 200
    assert "q999" in r.json()["skipped_unknown"]


def test_submit_answers_unknown_proposal_404():
    r = client.post(
        "/v1/agent-builder/advisory/proposals/gone/clarifications/answers",
        json={"answers": []},
    )
    assert r.status_code == 404


# ── POST /mappings/{key}/confirm ──────────────────────────────────────────────

def test_confirm_mapping():
    _, proposal_id = _make_eligible_proposal()
    r = client.post(
        f"/v1/agent-builder/advisory/proposals/{proposal_id}/mappings/state/confirm",
        json={"reason": "Correct"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["action"] == "confirmed"
    assert body["mapping_key"] == "state"
    assert body["is_advisory_only"] is True


def test_confirm_mapping_unknown_proposal_404():
    r = client.post(
        "/v1/agent-builder/advisory/proposals/gone/mappings/state/confirm",
        json={},
    )
    assert r.status_code == 404


# ── POST /mappings/{key}/reject ───────────────────────────────────────────────

def test_reject_mapping():
    _, proposal_id = _make_eligible_proposal()
    r = client.post(
        f"/v1/agent-builder/advisory/proposals/{proposal_id}/mappings/partner_id/reject",
        json={"reason": "Wrong model"},
    )
    assert r.status_code == 200
    assert r.json()["action"] == "rejected"


# ── GET /clarification-status ─────────────────────────────────────────────────

def test_clarification_status():
    _, proposal_id = _make_eligible_proposal()
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarification-status")
    assert r.status_code == 200
    body = r.json()
    assert "questions_total" in body
    assert "overall_complete" in body
    assert body["is_advisory_only"] is True
    assert body["can_execute"] is False


def test_clarification_status_unknown_proposal_404():
    r = client.get("/v1/agent-builder/advisory/proposals/gone/clarification-status")
    assert r.status_code == 404


# ── POST /drafts/{id}/refresh-from-clarifications ─────────────────────────────

def test_refresh_draft_from_clarifications():
    _, proposal_id = _make_eligible_proposal()
    draft_id = _make_draft(proposal_id)
    r = client.post(f"/v1/agent-builder/advisory/drafts/{draft_id}/refresh-from-clarifications")
    assert r.status_code == 200
    body = r.json()
    assert body["draft_id"] == draft_id
    assert body["runtime_mode"] == "dry_run_only"
    assert body["write_actions"] is False
    assert body["can_execute"] is False


def test_refresh_draft_unknown_draft_404():
    r = client.post("/v1/agent-builder/advisory/drafts/automation_draft_gone/refresh-from-clarifications")
    assert r.status_code == 404


# ── GET /clarification-audit ──────────────────────────────────────────────────

def test_clarification_audit_empty():
    _, proposal_id = _make_eligible_proposal()
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarification-audit")
    assert r.status_code == 200
    body = r.json()
    assert "event_count" in body
    assert "events" in body
    assert body["is_advisory_only"] is True


def test_clarification_audit_after_actions():
    _, proposal_id = _make_eligible_proposal()
    client.post(
        f"/v1/agent-builder/advisory/proposals/{proposal_id}/mappings/state/confirm",
        json={"reason": "ok"},
    )
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/clarification-audit")
    assert r.json()["event_count"] >= 1


def test_clarification_audit_unknown_proposal_404():
    r = client.get("/v1/agent-builder/advisory/proposals/gone/clarification-audit")
    assert r.status_code == 404
