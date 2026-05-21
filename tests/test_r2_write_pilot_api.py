from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import SessionLocal, init_db
from erpguard.db.repositories import create_skill, create_skill_version

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


def _make_skill() -> str:
    session = SessionLocal()
    try:
        skill = create_skill(session, name="R2 API Test Skill", description=None)
        create_skill_version(
            session, skill.id, "1.0",
            json.dumps({"guards": [], "steps": []}),
            "deterministic_browser", False,
        )
        return skill.id
    finally:
        session.close()


def _create_request(skill_id: str, record_id: int = 1, vals: dict | None = None) -> dict:
    resp = client.post(f"/v1/product/skills/{skill_id}/r2-write-pilot/request", json={
        "requested_by": {"type": "user", "id": "op1"},
        "approver_1": {"type": "user", "id": "ap1"},
        "approver_2": {"type": "user", "id": "ap2"},
        "target_record_id": record_id,
        "vals": vals or {"comment": "API test note"},
        "environment": "staging",
    })
    return resp.json()


# ── POST /v1/product/skills/{skill_id}/r2-write-pilot/request ──────────────

def test_create_r2_request():
    sid = _make_skill()
    resp = client.post(f"/v1/product/skills/{sid}/r2-write-pilot/request", json={
        "requested_by": {"id": "op1"},
        "approver_1": {"id": "ap1"},
        "approver_2": {"id": "ap2"},
        "target_record_id": 10,
        "vals": {"comment": "Sprint 10B test"},
        "environment": "staging",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"].startswith("r2req_")
    assert body["target_model"] == "res.partner"
    assert body["target_record_id"] == 10
    assert "comment" in body["target_fields"]
    assert body["environment"] == "staging"
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False


def test_create_r2_request_disallowed_field_returns_400():
    sid = _make_skill()
    resp = client.post(f"/v1/product/skills/{sid}/r2-write-pilot/request", json={
        "requested_by": {"id": "op1"},
        "approver_1": {"id": "ap1"},
        "approver_2": {"id": "ap2"},
        "target_record_id": 1,
        "vals": {"name": "Evil"},
        "environment": "staging",
    })
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "invalid_request"


def test_create_r2_request_skill_not_found():
    resp = client.post("/v1/product/skills/skill_nonexistent/r2-write-pilot/request", json={
        "requested_by": {}, "approver_1": {"id": "a"}, "approver_2": {"id": "b"},
        "target_record_id": 1, "vals": {"comment": "x"}, "environment": "staging",
    })
    assert resp.status_code == 404


def test_create_r2_request_idempotency():
    sid = _make_skill()
    b1 = _create_request(sid, record_id=99, vals={"comment": "idem"})
    b2 = _create_request(sid, record_id=99, vals={"comment": "idem"})
    assert b1["request_id"] == b2["request_id"]


# ── POST /v1/product/r2-write-pilot/requests/{id}/policy-check ────────────

def test_policy_check_blocked_by_feature_flag():
    sid = _make_skill()
    req = _create_request(sid)
    resp = client.post(f"/v1/product/r2-write-pilot/requests/{req['request_id']}/policy-check")
    assert resp.status_code == 200
    body = resp.json()
    assert body["passed"] is False
    assert body["allow_r2_real_write_pilot"] is False
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False
    codes = [v["code"] for v in body["violations"]]
    assert "feature_flag_disabled" in codes


def test_policy_check_target_model_whitelisted():
    sid = _make_skill()
    req = _create_request(sid)
    resp = client.post(f"/v1/product/r2-write-pilot/requests/{req['request_id']}/policy-check")
    body = resp.json()
    assert body["target_model"] == "res.partner"
    assert body["target_model_whitelisted"] is True
    assert "comment" in body["target_fields"]


def test_policy_check_request_not_found():
    resp = client.post("/v1/product/r2-write-pilot/requests/r2req_bad/policy-check")
    assert resp.status_code == 404


# ── POST /v1/product/r2-write-pilot/requests/{id}/execute ─────────────────

def test_execute_r2_blocked_by_default():
    sid = _make_skill()
    req = _create_request(sid)
    resp = client.post(f"/v1/product/r2-write-pilot/requests/{req['request_id']}/execute")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "blocked"
    assert body["executed_action"] == "blocked_by_feature_flag"
    assert body["allow_r2_real_write_pilot"] is False
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False


def test_execute_r2_idempotent():
    sid = _make_skill()
    req = _create_request(sid, record_id=77)
    rid = req["request_id"]
    r1 = client.post(f"/v1/product/r2-write-pilot/requests/{rid}/execute").json()
    r2 = client.post(f"/v1/product/r2-write-pilot/requests/{rid}/execute").json()
    assert r1["run_id"] == r2["run_id"]


# ── GET /v1/product/r2-write-pilot/runs/{run_id} ──────────────────────────

def test_get_r2_run():
    sid = _make_skill()
    req = _create_request(sid, record_id=88)
    run = client.post(f"/v1/product/r2-write-pilot/requests/{req['request_id']}/execute").json()
    resp = client.get(f"/v1/product/r2-write-pilot/runs/{run['run_id']}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["run_id"] == run["run_id"]
    assert body["status"] == "blocked"


def test_get_r2_run_not_found():
    resp = client.get("/v1/product/r2-write-pilot/runs/r2run_bad")
    assert resp.status_code == 404


# ── GET /v1/product/r2-write-pilot/runs/{run_id}/evidence ─────────────────

def test_get_r2_evidence():
    sid = _make_skill()
    req = _create_request(sid, record_id=55)
    run = client.post(f"/v1/product/r2-write-pilot/requests/{req['request_id']}/execute").json()
    resp = client.get(f"/v1/product/r2-write-pilot/runs/{run['run_id']}/evidence")
    assert resp.status_code == 200
    evidence = resp.json()
    assert isinstance(evidence, list)
    assert len(evidence) == 1
    ev = evidence[0]
    assert ev["action_taken"] == "blocked_by_feature_flag"
    assert ev["target_model"] == "res.partner"
    assert ev["allow_r2_real_write_pilot"] is False
    assert "rollback_instructions" in ev
    assert ev["rollback_instructions"]["model"] == "res.partner"


# ── GET /v1/product/skills/{skill_id}/r2-write-pilot/history ──────────────

def test_get_r2_history():
    sid = _make_skill()
    _create_request(sid, record_id=11, vals={"comment": "hist 1"})
    _create_request(sid, record_id=12, vals={"comment": "hist 2"})
    resp = client.get(f"/v1/product/skills/{sid}/r2-write-pilot/history")
    assert resp.status_code == 200
    history = resp.json()
    assert isinstance(history, list)
    assert len(history) >= 2
    for r in history:
        assert r["target_model"] == "res.partner"
        assert r["allow_generic_real_odoo_writes"] is False
        assert r["allow_r3_r4_real_writes"] is False


def test_get_r2_history_empty():
    sid = _make_skill()
    resp = client.get(f"/v1/product/skills/{sid}/r2-write-pilot/history")
    assert resp.status_code == 200
    assert resp.json() == []
