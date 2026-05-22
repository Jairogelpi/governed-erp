from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

_FAKE_ERP_URL = "http://localhost:8000/fake-erp"


def _create_session() -> str:
    r = client.post("/v1/record-to-skill/sessions", json={
        "name": "API Test Session",
        "description": "Sprint 20 API test",
        "target_base_url": _FAKE_ERP_URL,
    })
    assert r.status_code == 200
    return r.json()["session_id"]


def _capture_events(session_id: str):
    events = [
        {"event_type": "navigate", "url": _FAKE_ERP_URL + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
        {"event_type": "click", "selector": "[data-testid='open-order-SO-VALID']"},
        {"event_type": "click", "selector": "[data-testid='formula-tab']"},
        {"event_type": "click", "selector": "[data-testid='review-formula']"},
    ]
    for ev in events:
        r = client.post(f"/v1/record-to-skill/sessions/{session_id}/events", json=ev)
        assert r.status_code == 200


def _finish_session(session_id: str):
    r = client.post(f"/v1/record-to-skill/sessions/{session_id}/finish")
    assert r.status_code == 200


def _generate_draft(session_id: str) -> str:
    r = client.post(f"/v1/record-to-skill/sessions/{session_id}/generate-draft", json={
        "name": "API Test Skill",
        "description": "Auto-generated",
    })
    assert r.status_code == 200
    return r.json()["draft_id"]


def _compile_skill(draft_id: str) -> str:
    r = client.post(f"/v1/record-to-skill/drafts/{draft_id}/compile-ui-skill")
    assert r.status_code == 200
    return r.json()["compiled_skill_id"]


def _replay(compiled_skill_id: str) -> str:
    r = client.post(f"/v1/record-to-skill/compiled-skills/{compiled_skill_id}/replay", json={
        "target_base_url": _FAKE_ERP_URL,
    })
    assert r.status_code == 200
    return r.json()["replay_id"]


def test_create_session():
    r = client.post("/v1/record-to-skill/sessions", json={
        "name": "Test Session",
        "target_base_url": _FAKE_ERP_URL,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["session_id"].startswith("ui_session_")
    assert body["status"] == "recording"


def test_capture_event_returns_200():
    sid = _create_session()
    r = client.post(f"/v1/record-to-skill/sessions/{sid}/events", json={
        "event_type": "navigate",
        "url": _FAKE_ERP_URL + "/orders",
    })
    assert r.status_code == 200
    assert r.json()["event_index"] == 0


def test_capture_event_unknown_session_returns_404():
    r = client.post("/v1/record-to-skill/sessions/nonexistent/events", json={"event_type": "navigate"})
    assert r.status_code == 404


def test_finish_session():
    sid = _create_session()
    r = client.post(f"/v1/record-to-skill/sessions/{sid}/finish")
    assert r.status_code == 200
    assert r.json()["status"] == "finished"


def test_finish_nonexistent_session_returns_404():
    r = client.post("/v1/record-to-skill/sessions/nonexistent/finish")
    assert r.status_code == 404


def test_generate_draft_requires_finished_session():
    sid = _create_session()
    _capture_events(sid)
    r = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={"name": "Skill"})
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "session_not_finished"


def test_generate_draft_success():
    sid = _create_session()
    _capture_events(sid)
    _finish_session(sid)
    r = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={"name": "Formula Review"})
    assert r.status_code == 200
    body = r.json()
    assert body["draft_id"].startswith("ui_draft_")
    assert len(body["steps"]) > 0


def test_compile_skill_success():
    sid = _create_session()
    _capture_events(sid)
    _finish_session(sid)
    draft_id = _generate_draft(sid)
    r = client.post(f"/v1/record-to-skill/drafts/{draft_id}/compile-ui-skill")
    assert r.status_code == 200
    body = r.json()
    assert body["compiled_skill_id"].startswith("ui_skill_")
    assert body["runtime_type"] == "deterministic_ui"
    assert body["llm_required"] is False


def test_compile_nonexistent_draft_returns_404():
    r = client.post("/v1/record-to-skill/drafts/nonexistent_draft/compile-ui-skill")
    assert r.status_code == 404


def test_replay_success():
    sid = _create_session()
    _capture_events(sid)
    _finish_session(sid)
    did = _generate_draft(sid)
    csid = _compile_skill(did)
    r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/replay", json={"target_base_url": _FAKE_ERP_URL})
    assert r.status_code == 200
    body = r.json()
    assert body["replay_id"].startswith("ui_replay_")
    assert body["steps_passed"] > 0


def test_replay_rejects_non_fake_erp():
    sid = _create_session()
    _capture_events(sid)
    _finish_session(sid)
    did = _generate_draft(sid)
    csid = _compile_skill(did)
    r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/replay", json={"target_base_url": "http://prod-odoo.example.com"})
    assert r.status_code == 400


def test_get_audit_success():
    sid = _create_session()
    _capture_events(sid)
    _finish_session(sid)
    did = _generate_draft(sid)
    csid = _compile_skill(did)
    rid = _replay(csid)
    r = client.get(f"/v1/record-to-skill/replays/{rid}/audit")
    assert r.status_code == 200
    body = r.json()
    assert body["replay_id"] == rid
    assert len(body["entries"]) > 0


def test_get_audit_nonexistent_returns_404():
    r = client.get("/v1/record-to-skill/replays/nonexistent/audit")
    assert r.status_code == 404


def test_get_report_success():
    sid = _create_session()
    _capture_events(sid)
    _finish_session(sid)
    did = _generate_draft(sid)
    csid = _compile_skill(did)
    rid = _replay(csid)
    r = client.get(f"/v1/record-to-skill/replays/{rid}/report")
    assert r.status_code == 200
    body = r.json()
    assert body["replay_id"] == rid
    assert body["deterministic"] is True
    assert body["llm_used_at_replay"] is False
    assert body["success_rate_pct"] == 100.0


def test_get_report_nonexistent_returns_404():
    r = client.get("/v1/record-to-skill/replays/nonexistent/report")
    assert r.status_code == 404


def test_full_end_to_end_loop():
    sid = _create_session()
    _capture_events(sid)
    _finish_session(sid)
    did = _generate_draft(sid)
    csid = _compile_skill(did)
    rid = _replay(csid)

    audit_r = client.get(f"/v1/record-to-skill/replays/{rid}/audit")
    report_r = client.get(f"/v1/record-to-skill/replays/{rid}/report")

    assert audit_r.status_code == 200
    assert report_r.status_code == 200
    assert report_r.json()["summary"] != ""
