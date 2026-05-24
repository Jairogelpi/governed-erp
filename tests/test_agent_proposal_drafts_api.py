from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def _make_eligible_proposal() -> tuple[str, str]:
    """Returns (session_id, proposal_id) for a well-formed advisory proposal."""
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


# ── draft-preview ────────────────────────────────────────────────────────────

def test_draft_preview_returns_ready_for_eligible_proposal():
    _, proposal_id = _make_eligible_proposal()
    r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/draft-preview")
    assert r.status_code == 200
    body = r.json()
    assert body["eligible"] is True
    assert body["draft_runtime_mode"] == "dry_run_only"
    assert body["draft_write_actions"] is False
    assert body["draft_status"] == "pending_review"
    assert body["ready_to_create"] is True


def test_draft_preview_missing_proposal_returns_404():
    r = client.post("/v1/agent-builder/advisory/proposals/proposal_gone/draft-preview")
    assert r.status_code == 404


# ── create-draft ─────────────────────────────────────────────────────────────

def test_create_draft_produces_safe_automation_draft():
    _, proposal_id = _make_eligible_proposal()
    r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    assert r.status_code == 200
    body = r.json()
    assert body["draft_id"].startswith("automation_draft_")
    assert body["proposal_id"] == proposal_id
    assert body["runtime_mode"] == "dry_run_only"
    assert body["write_actions"] is False
    assert body["safety"]["can_execute"] is False
    assert body["safety"]["is_advisory_only"] is True
    assert body["safety"]["requires_human_review"] is True
    assert body["next_step"] == "human_review"


def test_create_draft_twice_returns_422():
    _, proposal_id = _make_eligible_proposal()
    client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "draft_creation_blocked"


def test_create_draft_missing_proposal_returns_404():
    r = client.post("/v1/agent-builder/advisory/proposals/proposal_gone/create-draft")
    assert r.status_code == 404


# ── draft-link ────────────────────────────────────────────────────────────────

def test_draft_link_no_draft_yet():
    _, proposal_id = _make_eligible_proposal()
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/draft-link")
    assert r.status_code == 200
    body = r.json()
    assert body["has_draft"] is False
    assert body["draft_id"] is None


def test_draft_link_after_create():
    _, proposal_id = _make_eligible_proposal()
    create_r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    draft_id = create_r.json()["draft_id"]

    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/draft-link")
    assert r.status_code == 200
    body = r.json()
    assert body["has_draft"] is True
    assert body["draft_id"] == draft_id


def test_draft_link_missing_proposal_returns_404():
    r = client.get("/v1/agent-builder/advisory/proposals/proposal_gone/draft-link")
    assert r.status_code == 404


# ── source-proposal (reverse lookup) ─────────────────────────────────────────

def test_source_proposal_reverse_lookup():
    _, proposal_id = _make_eligible_proposal()
    create_r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    draft_id = create_r.json()["draft_id"]

    r = client.get(f"/v1/agent-builder/advisory/drafts/{draft_id}/source-proposal")
    assert r.status_code == 200
    body = r.json()
    assert body["draft_id"] == draft_id
    assert body["proposal_id"] == proposal_id
    assert "proposal" in body


def test_source_proposal_missing_draft_returns_404():
    r = client.get("/v1/agent-builder/advisory/drafts/automation_draft_gone/source-proposal")
    assert r.status_code == 404


# ── safety invariants (non-regression) ───────────────────────────────────────

def test_draft_never_sets_can_execute_or_write_actions():
    _, proposal_id = _make_eligible_proposal()
    r = client.post(f"/v1/agent-builder/advisory/proposals/{proposal_id}/create-draft")
    body = r.json()
    assert body["write_actions"] is False
    assert body["safety"]["can_execute"] is False
    assert body["runtime_mode"] == "dry_run_only"


# ── demo dashboard marker ─────────────────────────────────────────────────────

def test_demo_dashboard_contains_draft_controls():
    r = client.get("/demo")
    assert r.status_code == 200
    assert "cabDraftPreview" in r.text
    assert "cabCreateDraft" in r.text
    assert "draft-preview" in r.text
    assert "create-draft" in r.text
