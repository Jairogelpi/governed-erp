from __future__ import annotations

from uuid import uuid4
from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)
_FAKE_ERP_BASE = "http://localhost:8000/fake-erp"


def _make_compiled_skill_id() -> str:
    r = client.post("/v1/record-to-skill/sessions", json={"name": "SV API Test", "target_base_url": _FAKE_ERP_BASE})
    sid = r.json()["session_id"]
    for ev in [
        {"event_type": "navigate", "url": _FAKE_ERP_BASE + "/sales/orders"},
        {"event_type": "fill", "selector": "[data-testid='order-search']", "input_value": "SO-VALID"},
        {"event_type": "click", "selector": "[data-testid='formula-tab']"},
    ]:
        client.post(f"/v1/record-to-skill/sessions/{sid}/events", json=ev)
    client.post(f"/v1/record-to-skill/sessions/{sid}/finish")
    dr = client.post(f"/v1/record-to-skill/sessions/{sid}/generate-draft", json={"name": "SV API Skill"})
    cr = client.post(f"/v1/record-to-skill/drafts/{dr.json()['draft_id']}/compile-ui-skill")
    return cr.json()["compiled_skill_id"]


def test_create_version_from_compiled_skill():
    csid = _make_compiled_skill_id()
    r = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["version_id"].startswith("ui_skv_")
    assert body["status"] == "draft"
    assert body["llm_required"] is False
    assert body["runtime_type"] == "deterministic_ui"


def test_create_version_nonexistent_compiled_skill_returns_404():
    r = client.post("/v1/skills/versioning/from-ui-compiled-skill/nonexistent_skill", json={})
    assert r.status_code == 404


def test_get_skill_version():
    csid = _make_compiled_skill_id()
    create_r = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={})
    vid = create_r.json()["version_id"]
    r = client.get(f"/v1/skills/versions/{vid}")
    assert r.status_code == 200
    assert r.json()["version_id"] == vid


def test_get_nonexistent_version_returns_404():
    r = client.get("/v1/skills/versions/nonexistent_version")
    assert r.status_code == 404


def test_list_skill_versions():
    csid = _make_compiled_skill_id()
    r = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={})
    skill_id = r.json()["skill_id"]
    lr = client.get(f"/v1/skills/{skill_id}/versions")
    assert lr.status_code == 200
    assert len(lr.json()) >= 1


def test_promotion_readiness():
    csid = _make_compiled_skill_id()
    vid = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={}).json()["version_id"]
    r = client.post(f"/v1/skills/versions/{vid}/promotion-readiness")
    assert r.status_code == 200
    body = r.json()
    assert "ready" in body
    assert "checks" in body


def test_full_lifecycle_progression():
    csid = _make_compiled_skill_id()
    vid = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={}).json()["version_id"]

    promote_r = client.post(f"/v1/skills/versions/{vid}/promote-candidate", json={"actor": "user1"})
    assert promote_r.status_code == 200
    assert promote_r.json()["to_status"] == "candidate"

    approve_r = client.post(f"/v1/skills/versions/{vid}/approve", json={"actor": "approver1"})
    assert approve_r.status_code == 200

    activate_r = client.post(f"/v1/skills/versions/{vid}/activate", json={"actor": "ops"})
    assert activate_r.status_code == 200
    assert activate_r.json()["to_status"] == "active"


def test_invalid_transition_returns_400():
    csid = _make_compiled_skill_id()
    vid = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={}).json()["version_id"]
    r = client.post(f"/v1/skills/versions/{vid}/approve", json={"actor": "skip"})
    assert r.status_code == 400


def test_activation_gate_blocks_draft():
    csid = _make_compiled_skill_id()
    vid = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={}).json()["version_id"]
    r = client.get(f"/v1/skills/versions/{vid}/activation-gate")
    assert r.status_code == 200
    assert r.json()["can_activate"] is False


def test_lifecycle_audit_has_events():
    csid = _make_compiled_skill_id()
    vid = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid}", json={}).json()["version_id"]
    r = client.get(f"/v1/skills/versions/{vid}/lifecycle-audit")
    assert r.status_code == 200
    assert len(r.json()["events"]) >= 1


def test_compare_versions():
    csid_a = _make_compiled_skill_id()
    csid_b = _make_compiled_skill_id()
    vid_a = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid_a}", json={}).json()["version_id"]
    vid_b = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid_b}", json={}).json()["version_id"]
    r = client.post("/v1/skills/versions/compare", json={"version_id_a": vid_a, "version_id_b": vid_b})
    assert r.status_code == 200
    assert "is_identical" in r.json()
    assert "summary" in r.json()


def test_rollback_flow():
    csid_a = _make_compiled_skill_id()
    csid_b = _make_compiled_skill_id()
    family_id = f"rollback_api_family_{uuid4().hex[:12]}"
    vid_a = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid_a}", json={"skill_id": family_id}).json()["version_id"]
    vid_b = client.post(f"/v1/skills/versioning/from-ui-compiled-skill/{csid_b}", json={"skill_id": family_id}).json()["version_id"]

    for vid in [vid_a, vid_b]:
        client.post(f"/v1/skills/versions/{vid}/promote-candidate", json={"actor": "u"})
        client.post(f"/v1/skills/versions/{vid}/approve", json={"actor": "a"})
    client.post(f"/v1/skills/versions/{vid_a}/activate", json={"actor": "o"})

    plan_r = client.post(f"/v1/skills/versions/{vid_a}/rollback-plan", json={"target_version_id": vid_b})
    assert plan_r.status_code == 200
    assert plan_r.json()["is_executable"] is True

    rb_r = client.post(f"/v1/skills/versions/{vid_a}/rollback-to/{vid_b}", json={"actor": "ops", "reason": "test"})
    assert rb_r.status_code == 200
    assert rb_r.json()["rolled_back_version_id"] == vid_a
    assert rb_r.json()["reactivated_version_id"] == vid_b
