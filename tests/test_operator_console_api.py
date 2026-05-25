"""Sprint 41 — Operator Console API integration tests."""
from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/operator/console"


def test_intents_endpoint():
    r = client.get(f"{BASE}/intents")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 8
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True
    intent_names = {i["intent"] for i in data["intents"]}
    assert "list_active_skills" in intent_names
    assert "governance_gaps" in intent_names


def test_create_session():
    r = client.post(f"{BASE}/sessions", json={"actor": "operator"})
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"].startswith("ocses_")
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_query_list_active():
    session_r = client.post(f"{BASE}/sessions", json={"actor": "operator"}).json()
    sid = session_r["session_id"]
    r = client.post(f"{BASE}/query", json={"query": "¿Qué skills tengo activas?", "session_id": sid})
    assert r.status_code == 200
    data = r.json()
    assert data["detected_intent"] == "list_active_skills"
    assert data["will_execute"] is False
    assert data["can_execute"] is False
    assert data["is_advisory_only"] is True
    assert data["response_message"] != ""


def test_query_governance_gaps():
    sid = client.post(f"{BASE}/sessions", json={"actor": "operator"}).json()["session_id"]
    r = client.post(f"{BASE}/query", json={"query": "qué falta para activar", "session_id": sid})
    assert r.status_code == 200
    data = r.json()
    assert data["detected_intent"] == "governance_gaps"


def test_query_next_step():
    sid = client.post(f"{BASE}/sessions", json={"actor": "operator"}).json()["session_id"]
    r = client.post(f"{BASE}/query", json={"query": "siguiente paso seguro", "session_id": sid})
    assert r.status_code == 200
    assert r.json()["will_execute"] is False


def test_session_history_empty_initially():
    sid = client.post(f"{BASE}/sessions", json={"actor": "operator"}).json()["session_id"]
    r = client.get(f"{BASE}/sessions/{sid}/history")
    assert r.status_code == 200
    data = r.json()
    assert data["entry_count"] == 0
    assert data["is_advisory_only"] is True


def test_session_history_accumulates():
    sid = client.post(f"{BASE}/sessions", json={"actor": "operator"}).json()["session_id"]
    client.post(f"{BASE}/query", json={"query": "skills activas", "session_id": sid})
    client.post(f"{BASE}/query", json={"query": "siguiente paso", "session_id": sid})
    r = client.get(f"{BASE}/sessions/{sid}/history")
    assert r.json()["entry_count"] == 2


def test_query_produces_follow_up_suggestions():
    sid = client.post(f"{BASE}/sessions", json={"actor": "operator"}).json()["session_id"]
    r = client.post(f"{BASE}/query", json={"query": "skills activas", "session_id": sid})
    data = r.json()
    assert isinstance(data["follow_up_suggestions"], list)


def test_safety_invariants_all_endpoints():
    sid = client.post(f"{BASE}/sessions", json={"actor": "operator"}).json()["session_id"]
    responses = [
        client.get(f"{BASE}/intents").json(),
        client.post(f"{BASE}/sessions", json={"actor": "operator"}).json(),
        client.post(f"{BASE}/query", json={"query": "lista activa", "session_id": sid}).json(),
        client.get(f"{BASE}/sessions/{sid}/history").json(),
    ]
    for resp in responses:
        assert resp.get("will_execute") is False, f"will_execute: {resp}"
        assert resp.get("can_execute") is False, f"can_execute: {resp}"
        assert resp.get("is_advisory_only") is True, f"is_advisory_only: {resp}"
