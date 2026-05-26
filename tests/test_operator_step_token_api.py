"""Sprint 43 — Step preview and confirmation token API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/operator-console/action-plan"


def _plan_id() -> str:
    r = client.post("/v1/operator-console/action-plan", json={"goal": "preparar para preview"})
    return r.json()["plan_id"]


def _preview(plan_id: str = "aplan_demo", step: int = 1,
             endpoint: str = "GET /v1/foo", method: str = "GET",
             severity: str = "required") -> dict:
    r = client.post(f"{BASE}/step-preview", json={
        "plan_id": plan_id,
        "step_number": step,
        "step_title": "Test step",
        "endpoint_hint": endpoint,
        "method_hint": method,
        "severity": severity,
    })
    assert r.status_code == 200
    return r.json()


def test_step_preview_returns_token():
    data = _preview()
    assert data["token_id"].startswith("tok_")
    assert data["status"] == "pending"
    assert data["ttl_seconds"] == 300


def test_step_preview_advisory_only():
    data = _preview()
    assert data["will_execute"] is False
    assert data["can_execute"] is False
    assert data["is_advisory_only"] is True


def test_step_preview_risk_fields_present():
    data = _preview()
    assert "risk_level" in data
    assert "risk_summary" in data
    assert data["risk_level"] in ("low", "medium", "high")


def test_step_preview_high_risk_activation():
    data = _preview(
        endpoint="POST /v1/agent-candidate-activation/ver_1",
        method="POST",
    )
    assert data["risk_level"] == "high"


def test_step_preview_low_risk_get():
    data = _preview(endpoint="GET /v1/agent-builder/versions/ver_1", method="GET")
    assert data["risk_level"] == "low"


def test_step_preview_with_real_plan_id():
    pid = _plan_id()
    data = _preview(plan_id=pid, step=1)
    assert data["plan_id"] == pid


def test_get_token_status():
    tid = _preview()["token_id"]
    r = client.get(f"{BASE}/step-preview/{tid}")
    assert r.status_code == 200
    data = r.json()
    assert data["token_id"] == tid
    assert data["status"] == "pending"
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_get_token_status_404():
    r = client.get(f"{BASE}/step-preview/tok_nonexistent_xyz")
    assert r.status_code == 404


def test_confirm_token():
    tid = _preview()["token_id"]
    r = client.post(f"{BASE}/step-confirm", json={"token_id": tid})
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "confirmed"
    assert data["confirmed_at"] is not None
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True
    assert len(data["message"]) > 0


def test_confirm_token_not_found():
    r = client.post(f"{BASE}/step-confirm", json={"token_id": "tok_nonexistent"})
    assert r.status_code == 200
    assert r.json()["status"] == "not_found"


def test_confirm_token_already_confirmed():
    tid = _preview()["token_id"]
    client.post(f"{BASE}/step-confirm", json={"token_id": tid})
    r = client.post(f"{BASE}/step-confirm", json={"token_id": tid})
    assert r.json()["status"] == "already_confirmed"


def test_token_status_after_confirm():
    tid = _preview()["token_id"]
    client.post(f"{BASE}/step-confirm", json={"token_id": tid})
    status = client.get(f"{BASE}/step-preview/{tid}").json()
    assert status["status"] == "confirmed"
    assert status["confirmed_at"] is not None


def test_safety_invariants_all_new_endpoints():
    tid = _preview()["token_id"]
    responses = [
        _preview(),
        client.get(f"{BASE}/step-preview/{tid}").json(),
        client.post(f"{BASE}/step-confirm", json={"token_id": tid}).json(),
    ]
    for resp in responses:
        assert resp.get("will_execute") is False
        assert resp.get("can_execute") is False
        assert resp.get("is_advisory_only") is True
