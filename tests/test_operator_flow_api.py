from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db
from erpguard.db.repositories import update_operator_session

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


def _create_session() -> str:
    resp = client.post("/v1/product/operator-sessions")
    assert resp.status_code == 200
    return resp.json()["session_id"]


# ── POST /v1/product/operator-sessions ────────────────────────────────────

def test_create_operator_session():
    resp = client.post("/v1/product/operator-sessions")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"].startswith("opsession_")
    assert body["current_step"] == "awaiting_tenant"
    assert body["status"] == "active"


# ── GET /v1/product/operator-sessions/{session_id} ─────────────────────────

def test_get_operator_session():
    sid = _create_session()
    resp = client.get(f"/v1/product/operator-sessions/{sid}")
    assert resp.status_code == 200
    assert resp.json()["session_id"] == sid


def test_get_operator_session_not_found():
    resp = client.get("/v1/product/operator-sessions/opsession_nonexistent_xyz")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "session_not_found"


# ── POST /v1/product/operator-sessions/{session_id}/select-tenant ──────────

def test_select_tenant():
    sid = _create_session()
    resp = client.post(f"/v1/product/operator-sessions/{sid}/select-tenant",
                       json={"tenant_id": "tenant_demo_abc"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == "tenant_demo_abc"
    assert body["current_step"] == "awaiting_connection"
    assert body["known_ids"]["tenant_id"] == "tenant_demo_abc"


# ── POST /v1/product/operator-sessions/{session_id}/select-connection ──────

def test_select_connection():
    sid = _create_session()
    client.post(f"/v1/product/operator-sessions/{sid}/select-tenant",
                json={"tenant_id": "tenant_demo_abc"})
    resp = client.post(f"/v1/product/operator-sessions/{sid}/select-connection",
                       json={"connection_id": "conn_demo_xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["connection_id"] == "conn_demo_xyz"
    assert body["current_step"] == "run_diagnosis"
    assert body["known_ids"]["connection_id"] == "conn_demo_xyz"


# ── POST /v1/product/operator-sessions/{session_id}/select-opportunity ─────

def test_select_opportunity_with_id():
    from erpguard.db.session import SessionLocal
    sid = _create_session()
    session = SessionLocal()
    try:
        update_operator_session(
            session, sid,
            current_step="select_opportunity",
            known_ids_json=json.dumps({"opportunity_ids": ["opp_abc", "opp_xyz"]}),
        )
    finally:
        session.close()
    resp = client.post(f"/v1/product/operator-sessions/{sid}/select-opportunity",
                       json={"opportunity_id": "opp_xyz"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["known_ids"]["opportunity_id"] == "opp_xyz"
    assert body["current_step"] == "create_draft"


def test_select_opportunity_auto_picks_first():
    from erpguard.db.session import SessionLocal
    sid = _create_session()
    session = SessionLocal()
    try:
        update_operator_session(
            session, sid,
            current_step="select_opportunity",
            known_ids_json=json.dumps({"opportunity_ids": ["opp_first", "opp_second"]}),
        )
    finally:
        session.close()
    resp = client.post(f"/v1/product/operator-sessions/{sid}/select-opportunity",
                       json={})
    assert resp.status_code == 200
    assert resp.json()["known_ids"]["opportunity_id"] == "opp_first"


def test_select_opportunity_no_opportunities_returns_400():
    sid = _create_session()
    from erpguard.db.session import SessionLocal
    session = SessionLocal()
    try:
        update_operator_session(session, sid, current_step="select_opportunity")
    finally:
        session.close()
    resp = client.post(f"/v1/product/operator-sessions/{sid}/select-opportunity",
                       json={})
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "no_opportunities"


# ── POST /v1/product/operator-sessions/{session_id}/run-next ───────────────

def test_run_next_executes_awaiting_tenant():
    sid = _create_session()
    resp = client.post(f"/v1/product/operator-sessions/{sid}/run-next")
    assert resp.status_code == 200
    body = resp.json()
    assert body["step_status"] == "ok"
    assert body["known_ids"].get("tenant_id") is not None
    assert body["current_step"] == "awaiting_connection"


def test_run_next_blocks_at_awaiting_connection():
    sid = _create_session()
    client.post(f"/v1/product/operator-sessions/{sid}/run-next")  # runs awaiting_tenant
    resp = client.post(f"/v1/product/operator-sessions/{sid}/run-next")
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_step"] == "awaiting_connection"
    assert "awaiting_connection" in body["message"] or "input" in body["message"].lower()


def test_run_next_session_not_found():
    resp = client.post("/v1/product/operator-sessions/opsession_bad/run-next")
    assert resp.status_code == 404


def test_run_next_optional_write_pilot_blocked():
    from erpguard.db.session import SessionLocal
    sid = _create_session()
    session = SessionLocal()
    try:
        update_operator_session(
            session, sid,
            current_step="optional_r1_write_pilot",
            known_ids_json=json.dumps({"skill_id": "skill_test"}),
        )
    finally:
        session.close()
    resp = client.post(f"/v1/product/operator-sessions/{sid}/run-next")
    assert resp.status_code == 200
    body = resp.json()
    assert body["step_status"] == "ok"
    assert "blocked" in body["message"].lower()


# ── POST /v1/product/operator-sessions/{session_id}/run-safe-readonly-path ─

def test_run_safe_readonly_path_runs_at_least_one_step():
    sid = _create_session()
    resp = client.post(f"/v1/product/operator-sessions/{sid}/run-safe-readonly-path")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["steps_executed"]) >= 1
    assert "awaiting_tenant" in body["steps_executed"]


def test_run_safe_readonly_path_stops_at_connection_block():
    sid = _create_session()
    resp = client.post(f"/v1/product/operator-sessions/{sid}/run-safe-readonly-path")
    body = resp.json()
    assert body["current_step"] == "awaiting_connection"


# ── GET /v1/product/operator-sessions/{session_id}/timeline ────────────────

def test_get_timeline_empty():
    sid = _create_session()
    resp = client.get(f"/v1/product/operator-sessions/{sid}/timeline")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == sid
    assert isinstance(body["events"], list)


def test_get_timeline_has_events_after_run():
    sid = _create_session()
    client.post(f"/v1/product/operator-sessions/{sid}/run-next")
    resp = client.get(f"/v1/product/operator-sessions/{sid}/timeline")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["events"]) >= 1
    assert "awaiting_tenant" in body["steps_completed"]


def test_get_timeline_not_found():
    resp = client.get("/v1/product/operator-sessions/opsession_bad/timeline")
    assert resp.status_code == 404


# ── GET /v1/product/operator-sessions/{session_id}/summary ─────────────────

def test_get_summary():
    sid = _create_session()
    resp = client.get(f"/v1/product/operator-sessions/{sid}/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == sid
    assert body["status"] == "active"
    assert 0 <= body["progress_pct"] <= 100
    assert body["steps_total"] > 0


def test_get_summary_safety_invariants():
    sid = _create_session()
    resp = client.get(f"/v1/product/operator-sessions/{sid}/summary")
    body = resp.json()
    inv = body["safety_invariants"]
    assert inv["can_execute_real_writes"] is False
    assert inv["allow_generic_real_odoo_writes"] is False
    assert inv["allow_r3_r4_real_writes"] is False


def test_get_summary_not_found():
    resp = client.get("/v1/product/operator-sessions/opsession_bad/summary")
    assert resp.status_code == 404
