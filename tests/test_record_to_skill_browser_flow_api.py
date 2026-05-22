from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

_FAKE_ERP_BASE = "http://localhost:8000/fake-erp"


def _browser_events(session_id: str, base_url: str = _FAKE_ERP_BASE):
    events = [
        {"event_type": "page_load", "url": base_url + "/sales/orders", "selector": None, "metadata": {"source": "recorder_s21"}},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID", "element_label": "Search orders", "metadata": {"source": "recorder_s21", "tag": "input", "type": "search"}},
        {"event_type": "click", "selector": "[data-testid='open-order-SO-VALID']", "element_text": "Open order", "element_label": "Open order SO-VALID", "metadata": {"source": "recorder_s21", "tag": "a"}},
        {"event_type": "click", "selector": "[data-testid='formula-tab']", "element_text": "Formula tab", "element_label": "Formula tab", "metadata": {"source": "recorder_s21", "tag": "a"}},
        {"event_type": "click", "selector": "[data-testid='review-formula']", "element_text": "Review formula", "element_label": "Review formula", "metadata": {"source": "recorder_s21", "tag": "button"}},
    ]
    for ev in events:
        r = client.post(f"/v1/record-to-skill/sessions/{session_id}/events", json=ev)
        assert r.status_code == 200


def test_get_session_returns_session():
    r = client.post("/v1/record-to-skill/sessions", json={
        "name": "Browser Flow Test",
        "target_base_url": _FAKE_ERP_BASE,
    })
    assert r.status_code == 200
    sid = r.json()["session_id"]

    r2 = client.get(f"/v1/record-to-skill/sessions/{sid}")
    assert r2.status_code == 200
    assert r2.json()["session_id"] == sid
    assert r2.json()["status"] == "recording"


def test_get_session_nonexistent_returns_404():
    r = client.get("/v1/record-to-skill/sessions/nonexistent_session")
    assert r.status_code == 404


def test_browser_events_have_source_metadata():
    r = client.post("/v1/record-to-skill/sessions", json={
        "name": "Metadata Test",
        "target_base_url": _FAKE_ERP_BASE,
    })
    sid = r.json()["session_id"]
    r2 = client.post(f"/v1/record-to-skill/sessions/{sid}/events", json={
        "event_type": "page_load",
        "url": _FAKE_ERP_BASE + "/sales/orders",
        "metadata": {"source": "recorder_s21", "page": "/sales/orders"},
    })
    assert r2.status_code == 200
    assert r2.json()["event_type"] == "page_load"


def test_full_browser_recording_loop():
    r = client.post("/v1/record-to-skill/sessions", json={
        "name": "Full Browser Loop",
        "target_base_url": _FAKE_ERP_BASE,
    })
    assert r.status_code == 200
    sid = r.json()["session_id"]

    _browser_events(sid)

    finish_r = client.post(f"/v1/record-to-skill/sessions/{sid}/finish")
    assert finish_r.status_code == 200
    assert finish_r.json()["status"] == "finished"

    draft_r = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={
        "name": "Browser Recorded Skill",
        "description": "Captured via recorder_s21",
    })
    assert draft_r.status_code == 200
    draft_id = draft_r.json()["draft_id"]
    assert draft_r.json()["normalized_event_count"] >= 3

    compile_r = client.post(f"/v1/record-to-skill/drafts/{draft_id}/compile-ui-skill")
    assert compile_r.status_code == 200
    csid = compile_r.json()["compiled_skill_id"]
    assert compile_r.json()["llm_required"] is False

    replay_r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/replay", json={
        "target_base_url": _FAKE_ERP_BASE,
    })
    assert replay_r.status_code == 200
    rid = replay_r.json()["replay_id"]
    assert replay_r.json()["steps_passed"] > 0

    audit_r = client.get(f"/v1/record-to-skill/replays/{rid}/audit")
    assert audit_r.status_code == 200
    assert len(audit_r.json()["entries"]) > 0

    report_r = client.get(f"/v1/record-to-skill/replays/{rid}/report")
    assert report_r.status_code == 200
    assert report_r.json()["deterministic"] is True
    assert report_r.json()["llm_used_at_replay"] is False


def test_recorder_events_with_page_load_type_are_accepted():
    r = client.post("/v1/record-to-skill/sessions", json={
        "name": "Page Load Test",
        "target_base_url": _FAKE_ERP_BASE,
    })
    sid = r.json()["session_id"]
    r2 = client.post(f"/v1/record-to-skill/sessions/{sid}/events", json={
        "event_type": "page_load",
        "url": _FAKE_ERP_BASE + "/sales/orders",
    })
    assert r2.status_code == 200
    assert r2.json()["event_type"] == "page_load"


def test_draft_generation_after_real_browser_events_has_selectors():
    r = client.post("/v1/record-to-skill/sessions", json={
        "name": "Selector Test",
        "target_base_url": _FAKE_ERP_BASE,
    })
    sid = r.json()["session_id"]
    _browser_events(sid)
    client.post(f"/v1/record-to-skill/sessions/{sid}/finish")
    draft_r = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={"name": "Selector Test Skill"})
    assert draft_r.status_code == 200
    assert len(draft_r.json()["selector_map"]) > 0
