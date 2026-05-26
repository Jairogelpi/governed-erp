"""Sprint 41B — Operator Console spec-compatible alias endpoint tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/operator-console"
ORIG = "/v1/operator/console"


def test_ask_auto_creates_session():
    r = client.post(f"{BASE}/ask", json={"question": "skills activas"})
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"].startswith("ocses_")
    assert data["detected_intent"] == "list_active_skills"
    assert data["will_execute"] is False
    assert data["can_execute"] is False
    assert data["is_advisory_only"] is True


def test_ask_with_existing_session_id():
    sid = client.post(f"{ORIG}/sessions", json={"actor": "operator"}).json()["session_id"]
    r = client.post(f"{BASE}/ask", json={"question": "governance gaps", "session_id": sid})
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == sid
    assert data["will_execute"] is False


def test_ask_with_version_id_passed_through():
    r = client.post(
        f"{BASE}/ask",
        json={"question": "siguiente paso", "version_id": "nonexistent-version-xyz"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["version_id_context"] == "nonexistent-version-xyz"


def test_ask_returns_response_message():
    r = client.post(f"{BASE}/ask", json={"question": "qué skills tengo activas"})
    assert r.status_code == 200
    assert r.json()["response_message"] != ""


def test_ask_safety_invariants():
    r = client.post(f"{BASE}/ask", json={"question": "lista de skills"}).json()
    assert r["will_execute"] is False
    assert r["can_execute"] is False
    assert r["is_advisory_only"] is True


def test_audit_global_returns_list():
    client.post(f"{BASE}/ask", json={"question": "skills activas"})
    r = client.get(f"{BASE}/audit")
    assert r.status_code == 200
    data = r.json()
    assert "entries" in data
    assert isinstance(data["entries"], list)
    assert data["entry_count"] >= 1
    assert data["session_id"] is None
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_audit_with_session_id_returns_history():
    sid = client.post(f"{ORIG}/sessions", json={"actor": "operator"}).json()["session_id"]
    client.post(f"{ORIG}/query", json={"query": "skills activas", "session_id": sid})
    r = client.get(f"{BASE}/audit", params={"session_id": sid})
    assert r.status_code == 200
    data = r.json()
    assert data["session_id"] == sid
    assert data["entry_count"] == 1
    assert data["is_advisory_only"] is True


def test_audit_global_limit_param():
    r = client.get(f"{BASE}/audit", params={"limit": 5})
    assert r.status_code == 200
    assert len(r.json()["entries"]) <= 5


def test_audit_global_entry_fields():
    client.post(f"{BASE}/ask", json={"question": "gaps de governance"})
    r = client.get(f"{BASE}/audit").json()
    if r["entries"]:
        entry = r["entries"][0]
        for field in ("query_id", "session_id", "query_text", "detected_intent",
                      "intent_confidence", "response_summary", "result_type", "created_at"):
            assert field in entry, f"missing field: {field}"
