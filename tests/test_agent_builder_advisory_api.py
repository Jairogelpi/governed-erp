from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)


def _create_session() -> str:
    r = client.post(
        "/v1/agent-builder/advisory/sessions",
        json={"created_by": {"type": "test", "id": "operator_1"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_advisory_only"] is True
    assert body["can_execute"] is False
    return body["session_id"]


def _create_proposal(session_id: str, text: str = "List all draft sales orders every day") -> str:
    r = client.post(
        f"/v1/agent-builder/advisory/sessions/{session_id}/propose",
        json={"request_text": text},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["is_advisory_only"] is True
    assert body["can_execute"] is False
    return body["proposal_id"]


# ── Session lifecycle ────────────────────────────────────────────────────────

def test_create_advisory_session():
    r = client.post(
        "/v1/agent-builder/advisory/sessions",
        json={"created_by": {"type": "demo_operator"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"].startswith("advisory_")
    assert body["status"] == "created"
    assert body["is_advisory_only"] is True


def test_get_advisory_session():
    session_id = _create_session()
    r = client.get(f"/v1/agent-builder/advisory/sessions/{session_id}")
    assert r.status_code == 200
    assert r.json()["session_id"] == session_id


def test_get_missing_session_returns_404():
    r = client.get("/v1/agent-builder/advisory/sessions/advisory_doesnotexist")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "advisory_not_found"


# ── Proposal lifecycle ───────────────────────────────────────────────────────

def test_propose_generates_full_advisory_proposal():
    session_id = _create_session()
    r = client.post(
        f"/v1/agent-builder/advisory/sessions/{session_id}/propose",
        json={"request_text": "Validate all draft sales orders formula daily at 8 AM"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["proposal_id"].startswith("proposal_")
    assert body["session_id"] == session_id
    assert body["is_advisory_only"] is True
    assert body["can_execute"] is False
    assert "workflow" in body
    assert "guards" in body
    assert "risk_summary" in body
    assert "clarification_questions" in body
    assert "safety_note" in body
    assert body["intent"]["is_advisory_only"] is True


def test_propose_empty_text_returns_422():
    session_id = _create_session()
    r = client.post(
        f"/v1/agent-builder/advisory/sessions/{session_id}/propose",
        json={"request_text": "   "},
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "empty_request_text"


def test_propose_on_missing_session_returns_404():
    r = client.post(
        "/v1/agent-builder/advisory/sessions/advisory_gone/propose",
        json={"request_text": "test"},
    )
    assert r.status_code == 404


def test_get_proposal():
    session_id = _create_session()
    proposal_id = _create_proposal(session_id)
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}")
    assert r.status_code == 200
    assert r.json()["proposal_id"] == proposal_id


def test_get_missing_proposal_returns_404():
    r = client.get("/v1/agent-builder/advisory/proposals/proposal_gone")
    assert r.status_code == 404


def test_revise_proposal():
    session_id = _create_session()
    proposal_id = _create_proposal(session_id)

    r = client.post(
        f"/v1/agent-builder/advisory/proposals/{proposal_id}/revise",
        json={"updated_request": "Send daily invoice email report to accountant"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["revision_number"] == 2
    assert body["status"] == "revised"
    assert body["is_advisory_only"] is True


def test_revise_empty_request_returns_422():
    session_id = _create_session()
    proposal_id = _create_proposal(session_id)
    r = client.post(
        f"/v1/agent-builder/advisory/proposals/{proposal_id}/revise",
        json={"updated_request": ""},
    )
    assert r.status_code == 422


def test_safety_summary_returns_invariants():
    session_id = _create_session()
    proposal_id = _create_proposal(session_id)
    r = client.get(f"/v1/agent-builder/advisory/proposals/{proposal_id}/safety")
    assert r.status_code == 200
    body = r.json()
    assert body["is_advisory_only"] is True
    assert body["can_execute"] is False
    assert len(body["safety_invariants"]) >= 4
    assert any("no ERP writes" in inv for inv in body["safety_invariants"])


def test_safety_summary_missing_proposal_returns_404():
    r = client.get("/v1/agent-builder/advisory/proposals/proposal_gone/safety")
    assert r.status_code == 404


# ── Demo dashboard marker ────────────────────────────────────────────────────

def test_demo_dashboard_contains_conversational_agent_builder():
    r = client.get("/demo")
    assert r.status_code == 200
    assert "Conversational Agent Builder" in r.text
    assert "cabCreateSession" in r.text
    assert "cabPropose" in r.text
    assert "advisory" in r.text


# ── Safety invariants (non-regression) ──────────────────────────────────────

def test_proposal_never_marks_can_execute_true():
    session_id = _create_session()
    for text in [
        "Confirm all sales orders",
        "Delete all invoices",
        "Update all partner emails",
        "Send emails to all customers",
    ]:
        r = client.post(
            f"/v1/agent-builder/advisory/sessions/{session_id}/propose",
            json={"request_text": text},
        )
        body = r.json()
        assert body.get("can_execute") is False, f"can_execute was True for: {text}"
        assert body.get("is_advisory_only") is True, f"is_advisory_only was False for: {text}"
