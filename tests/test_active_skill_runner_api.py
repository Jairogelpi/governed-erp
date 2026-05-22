from __future__ import annotations

from uuid import uuid4
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)
_FAKE_ERP_BASE = "http://localhost:8000/fake-erp"


def _make_active_version_id() -> tuple[str, str]:
    """Returns (version_id, skill_id)."""
    r = client.post("/v1/record-to-skill/sessions", json={"name": "ASR API", "target_base_url": _FAKE_ERP_BASE})
    sid = r.json()["session_id"]
    for ev in [
        {"event_type": "navigate", "url": _FAKE_ERP_BASE + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
        {"event_type": "click", "selector": "[data-testid='formula-tab']"},
    ]:
        client.post(f"/v1/record-to-skill/sessions/{sid}/events", json=ev)
    client.post(f"/v1/record-to-skill/sessions/{sid}/finish")
    dr = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={"name": "ASR API Skill"})
    cr = client.post(f"/v1/record-to-skill/drafts/{dr.json()['draft_id']}/compile-ui-skill")
    csid = cr.json()["compiled_skill_id"]
    skill_id = f"asr_api_family_{uuid4().hex[:12]}"
    vr = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={"skill_id": skill_id})
    vid = vr.json()["version_id"]
    client.post(f"/v1/skills/versions/{vid}/promote-candidate", json={"actor": "u"})
    client.post(f"/v1/skills/versions/{vid}/approve", json={"actor": "a"})
    client.post(f"/v1/skills/versions/{vid}/activate", json={"actor": "o"})
    return vid, skill_id


def test_manual_run_active_version():
    vid, _ = _make_active_version_id()
    r = client.post(f"/v1/skills/versions/{vid}/manual-run", json={
        "target_base_url": _FAKE_ERP_BASE,
        "actor": "test_op",
        "inputs": {"order_reference": "SO-VALID"},
    })
    assert r.status_code == 200
    body = r.json()
    assert body["run_id"].startswith("as_run_")
    assert body["status"] in ("completed", "completed_with_failures")


def test_manual_run_blocked_for_draft():
    r = client.post("/v1/record-to-skill/sessions", json={"name": "Draft ASR", "target_base_url": _FAKE_ERP_BASE})
    sid = r.json()["session_id"]
    for ev in [
        {"event_type": "navigate", "url": _FAKE_ERP_BASE + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
    ]:
        client.post(f"/v1/record-to-skill/sessions/{sid}/events", json=ev)
    client.post(f"/v1/record-to-skill/sessions/{sid}/finish")
    dr = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={"name": "Draft ASR Skill"})
    cr = client.post(f"/v1/record-to-skill/drafts/{dr.json()['draft_id']}/compile-ui-skill")
    csid = cr.json()["compiled_skill_id"]
    vr = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}",
                     json={"skill_id": f"draft_asr_{uuid4().hex[:12]}"})
    vid = vr.json()["version_id"]
    run_r = client.post(f"/v1/skills/versions/{vid}/manual-run", json={"target_base_url": _FAKE_ERP_BASE})
    assert run_r.status_code == 200
    assert run_r.json()["status"] == "blocked"


def test_manual_run_nonexistent_version_returns_404():
    r = client.post("/v1/skills/versions/nonexistent_version/manual-run",
                    json={"target_base_url": _FAKE_ERP_BASE})
    assert r.status_code == 404


def test_manual_run_invalid_target_rejected():
    vid, _ = _make_active_version_id()
    r = client.post(f"/v1/skills/versions/{vid}/manual-run", json={
        "target_base_url": "http://production-erp.example.com",
    })
    assert r.status_code == 200
    assert r.json()["status"] == "rejected"


def test_get_run_returns_summary():
    vid, _ = _make_active_version_id()
    run_r = client.post(f"/v1/skills/versions/{vid}/manual-run", json={"target_base_url": _FAKE_ERP_BASE})
    run_id = run_r.json()["run_id"]
    r = client.get(f"/v1/skills/runs/{run_id}")
    assert r.status_code == 200
    assert r.json()["run_id"] == run_id


def test_get_run_nonexistent_returns_404():
    r = client.get("/v1/skills/runs/nonexistent_run_id")
    assert r.status_code == 404


def test_get_run_events():
    vid, _ = _make_active_version_id()
    run_r = client.post(f"/v1/skills/versions/{vid}/manual-run", json={"target_base_url": _FAKE_ERP_BASE})
    run_id = run_r.json()["run_id"]
    r = client.get(f"/v1/skills/runs/{run_id}/events")
    assert r.status_code == 200
    assert r.json()["event_count"] >= 2


def test_get_run_events_nonexistent_returns_404():
    r = client.get("/v1/skills/runs/nonexistent_run_id/events")
    assert r.status_code == 404


def test_get_run_report():
    vid, _ = _make_active_version_id()
    run_r = client.post(f"/v1/skills/versions/{vid}/manual-run", json={"target_base_url": _FAKE_ERP_BASE})
    run_id = run_r.json()["run_id"]
    r = client.get(f"/v1/skills/runs/{run_id}/report")
    assert r.status_code == 200
    body = r.json()
    assert body["deterministic"] is True
    assert body["llm_used_at_replay"] is False
    assert "event_log" in body


def test_get_run_report_nonexistent_returns_404():
    r = client.get("/v1/skills/runs/nonexistent_run_id/report")
    assert r.status_code == 404


def test_list_runs_for_skill():
    vid, skill_id = _make_active_version_id()
    client.post(f"/v1/skills/versions/{vid}/manual-run", json={"target_base_url": _FAKE_ERP_BASE})
    client.post(f"/v1/skills/versions/{vid}/manual-run", json={"target_base_url": _FAKE_ERP_BASE})
    r = client.get(f"/v1/skills/{skill_id}/active-runs")
    assert r.status_code == 200
    assert len(r.json()) >= 2
