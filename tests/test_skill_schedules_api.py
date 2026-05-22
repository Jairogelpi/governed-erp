from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)
_FAKE_ERP_BASE = "http://localhost:8000/fake-erp"


def _make_active_version_id() -> tuple[str, str]:
    r = client.post("/v1/record-to-skill/sessions", json={"name": "Sch API", "target_base_url": _FAKE_ERP_BASE})
    sid = r.json()["session_id"]
    for ev in [
        {"event_type": "navigate", "url": _FAKE_ERP_BASE + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
        {"event_type": "click", "selector": "[data-testid='formula-tab']"},
    ]:
        client.post(f"/v1/record-to-skill/sessions/{sid}/events", json=ev)
    client.post(f"/v1/record-to-skill/sessions/{sid}/finish")
    dr = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={"name": "Sch API Skill"})
    cr = client.post(f"/v1/record-to-skill/drafts/{dr.json()['draft_id']}/compile-ui-skill")
    csid = cr.json()["compiled_skill_id"]
    skill_id = f"sch_api_family_{uuid4().hex[:12]}"
    vr = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={"skill_id": skill_id})
    vid = vr.json()["version_id"]
    client.post(f"/v1/skills/versions/{vid}/promote-candidate", json={"actor": "u"})
    client.post(f"/v1/skills/versions/{vid}/approve", json={"actor": "a"})
    client.post(f"/v1/skills/versions/{vid}/activate", json={"actor": "o"})
    return vid, skill_id


def _payload(name: str = "T", interval: int = 60) -> dict:
    return {
        "name": name,
        "interval_seconds": interval,
        "min_interval_seconds": 60,
        "dedup_window_seconds": 30,
        "target_base_url": _FAKE_ERP_BASE,
        "inputs": {},
        "created_by": "test_op",
    }


def test_create_schedule():
    vid, _ = _make_active_version_id()
    r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    assert r.status_code == 200
    body = r.json()
    assert body["schedule_id"].startswith("sch_")
    assert body["status"] == "draft"


def test_create_schedule_bad_interval():
    vid, _ = _make_active_version_id()
    r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload(interval=10))
    assert r.status_code == 400


def test_get_schedule():
    vid, _ = _make_active_version_id()
    create_r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    sid = create_r.json()["schedule_id"]
    r = client.get(f"/v1/skills/schedules/{sid}")
    assert r.status_code == 200
    assert r.json()["schedule_id"] == sid


def test_get_nonexistent_schedule_returns_404():
    r = client.get("/v1/skills/schedules/nonexistent_schedule")
    assert r.status_code == 404


def test_activate_schedule():
    vid, _ = _make_active_version_id()
    create_r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    sid = create_r.json()["schedule_id"]
    r = client.post(f"/v1/skills/schedules/{sid}/activate", json={"actor": "u", "reason": "test"})
    assert r.status_code == 200
    assert r.json()["status"] == "active"


def test_pause_resume_disable():
    vid, _ = _make_active_version_id()
    create_r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    sid = create_r.json()["schedule_id"]
    client.post(f"/v1/skills/schedules/{sid}/activate", json={"actor": "u"})
    pause_r = client.post(f"/v1/skills/schedules/{sid}/pause", json={"actor": "u"})
    assert pause_r.json()["status"] == "paused"
    resume_r = client.post(f"/v1/skills/schedules/{sid}/resume", json={"actor": "u"})
    assert resume_r.json()["status"] == "active"
    disable_r = client.post(f"/v1/skills/schedules/{sid}/disable", json={"actor": "u"})
    assert disable_r.json()["status"] == "disabled"


def test_invalid_transition_returns_400():
    vid, _ = _make_active_version_id()
    create_r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    sid = create_r.json()["schedule_id"]
    r = client.post(f"/v1/skills/schedules/{sid}/pause", json={"actor": "u"})
    assert r.status_code == 400


def test_get_schedule_events():
    vid, _ = _make_active_version_id()
    create_r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    sid = create_r.json()["schedule_id"]
    r = client.get(f"/v1/skills/schedules/{sid}/events")
    assert r.status_code == 200
    assert r.json()["event_count"] >= 1


def test_get_schedule_events_nonexistent_returns_404():
    r = client.get("/v1/skills/schedules/nonexistent/events")
    assert r.status_code == 404


def test_get_schedule_queue():
    vid, _ = _make_active_version_id()
    create_r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    sid = create_r.json()["schedule_id"]
    r = client.get(f"/v1/skills/schedules/{sid}/queue")
    assert r.status_code == 200
    assert r.json()["queue_entry_count"] == 0


def test_list_schedules_for_skill():
    vid, skill_id = _make_active_version_id()
    client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload(name="A"))
    client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload(name="B"))
    r = client.get(f"/v1/skills/{skill_id}/schedules")
    assert r.status_code == 200
    assert len(r.json()) >= 2


def test_tick_with_no_due_returns_empty():
    r = client.post("/v1/skills/schedules/tick", json={"now": "2000-01-01T00:00:00+00:00"})
    assert r.status_code == 200
    assert r.json()["due_count"] == 0


def test_tick_with_invalid_now_returns_400():
    r = client.post("/v1/skills/schedules/tick", json={"now": "not-a-date"})
    assert r.status_code == 400


def test_tick_dispatches_active_schedule():
    vid, _ = _make_active_version_id()
    create_r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    sid = create_r.json()["schedule_id"]
    client.post(f"/v1/skills/schedules/{sid}/activate", json={"actor": "u"})
    future = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
    r = client.post("/v1/skills/schedules/tick", json={"now": future})
    assert r.status_code == 200
    dispatched = [d for d in r.json()["dispatched"] if d["schedule_id"] == sid]
    assert len(dispatched) == 1


def test_full_schedule_flow():
    vid, skill_id = _make_active_version_id()
    create_r = client.post(f"/v1/skills/versions/{vid}/schedules", json=_payload())
    sid = create_r.json()["schedule_id"]

    client.post(f"/v1/skills/schedules/{sid}/activate", json={"actor": "u"})
    future = (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()
    client.post("/v1/skills/schedules/tick", json={"now": future})

    queue_r = client.get(f"/v1/skills/schedules/{sid}/queue")
    assert queue_r.json()["queue_entry_count"] >= 1

    events_r = client.get(f"/v1/skills/schedules/{sid}/events")
    types = [e["event_type"] for e in events_r.json()["events"]]
    assert "tick_dispatched" in types
