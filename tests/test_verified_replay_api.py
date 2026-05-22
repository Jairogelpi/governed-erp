from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
_FAKE_ERP_BASE = "http://localhost:8000/fake-erp"


def _make_compiled_skill_id() -> str:
    r = client.post("/v1/record-to-skill/sessions", json={
        "name": "Verified API Test", "target_base_url": _FAKE_ERP_BASE,
    })
    sid = r.json()["session_id"]
    events = [
        {"event_type": "navigate", "url": _FAKE_ERP_BASE + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
        {"event_type": "click", "selector": "[data-testid='open-order-SO-VALID']"},
        {"event_type": "click", "selector": "[data-testid='formula-tab']"},
        {"event_type": "click", "selector": "[data-testid='review-formula']"},
    ]
    for ev in events:
        client.post(f"/v1/record-to-skill/sessions/{sid}/events", json=ev)
    client.post(f"/v1/record-to-skill/sessions/{sid}/finish")
    draft_r = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={"name": "Sprint22 API Test"})
    compile_r = client.post(f"/v1/record-to-skill/drafts/{draft_r.json()['draft_id']}/compile-ui-skill")
    return compile_r.json()["compiled_skill_id"]


def test_verified_replay_returns_200():
    csid = _make_compiled_skill_id()
    r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/verified-replay", json={"target_base_url": _FAKE_ERP_BASE})
    assert r.status_code == 200
    body = r.json()
    assert body["replay_id"].startswith("ui_replay_")
    assert "steps_verification_failed" in body


def test_verified_replay_rejects_non_fake_erp():
    csid = _make_compiled_skill_id()
    r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/verified-replay", json={"target_base_url": "http://prod-erp.example.com"})
    assert r.status_code == 400


def test_verified_replay_step_results_have_verification_status():
    csid = _make_compiled_skill_id()
    r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/verified-replay", json={"target_base_url": _FAKE_ERP_BASE})
    body = r.json()
    for step in body["step_results"]:
        assert "verification_status" in step
        assert "checks" in step
        assert "failure_type" in step
        assert "recovery_suggestion" in step


def test_get_verification_returns_200():
    csid = _make_compiled_skill_id()
    replay_r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/verified-replay", json={"target_base_url": _FAKE_ERP_BASE})
    rid = replay_r.json()["replay_id"]
    r = client.get(f"/v1/record-to-skill/replays/{rid}/verification")
    assert r.status_code == 200
    body = r.json()
    assert body["replay_id"] == rid
    assert len(body["verifications"]) > 0


def test_get_verification_nonexistent_returns_404():
    r = client.get("/v1/record-to-skill/replays/nonexistent/verification")
    assert r.status_code == 404


def test_get_failures_returns_200():
    csid = _make_compiled_skill_id()
    replay_r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/verified-replay", json={"target_base_url": _FAKE_ERP_BASE})
    rid = replay_r.json()["replay_id"]
    r = client.get(f"/v1/record-to-skill/replays/{rid}/failures")
    assert r.status_code == 200
    body = r.json()
    assert body["replay_id"] == rid
    assert "failure_count" in body
    assert "failures" in body


def test_get_failures_nonexistent_returns_404():
    r = client.get("/v1/record-to-skill/replays/nonexistent/failures")
    assert r.status_code == 404


def test_get_robust_report_returns_200():
    csid = _make_compiled_skill_id()
    replay_r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/verified-replay", json={"target_base_url": _FAKE_ERP_BASE})
    rid = replay_r.json()["replay_id"]
    r = client.get(f"/v1/record-to-skill/replays/{rid}/robust-report")
    assert r.status_code == 200
    body = r.json()
    assert body["replay_id"] == rid
    assert body["deterministic"] is True
    assert body["llm_used_at_replay"] is False
    assert "verification_count" in body
    assert "failure_count" in body
    assert "recovery_actions_required" in body
    assert "summary" in body


def test_get_robust_report_nonexistent_returns_404():
    r = client.get("/v1/record-to-skill/replays/nonexistent/robust-report")
    assert r.status_code == 404


def test_full_verified_replay_loop():
    csid = _make_compiled_skill_id()
    replay_r = client.post(f"/v1/record-to-skill/compiled-skills/{csid}/verified-replay", json={"target_base_url": _FAKE_ERP_BASE})
    assert replay_r.status_code == 200
    rid = replay_r.json()["replay_id"]

    verif_r = client.get(f"/v1/record-to-skill/replays/{rid}/verification")
    fail_r = client.get(f"/v1/record-to-skill/replays/{rid}/failures")
    robust_r = client.get(f"/v1/record-to-skill/replays/{rid}/robust-report")

    assert verif_r.status_code == 200
    assert fail_r.status_code == 200
    assert robust_r.status_code == 200
    assert robust_r.json()["summary"] != ""
