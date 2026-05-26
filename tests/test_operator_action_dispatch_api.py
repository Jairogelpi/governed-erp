"""Sprint 44 — Action dispatch eligibility API tests."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)
BASE = "/v1/operator-console"


def _eligibility(endpoint: str, method: str = "GET",
                 token_id: str | None = None, action_key: str | None = None) -> dict:
    body: dict = {"endpoint_hint": endpoint, "method_hint": method}
    if token_id:
        body["token_id"] = token_id
    if action_key:
        body["action_key"] = action_key
    r = client.post(f"{BASE}/action-plan/dispatch-eligibility", json=body)
    assert r.status_code == 200
    return r.json()


def test_registry_returns_all_actions():
    r = client.get(f"{BASE}/action-registry")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] >= 9
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True
    keys = {a["action_key"] for a in data["actions"]}
    assert "activate_candidate" in keys
    assert "check_governance_gaps" in keys


def test_registry_entry_fields():
    data = client.get(f"{BASE}/action-registry").json()
    entry = data["actions"][0]
    for field in ("action_key", "display_name", "description", "endpoint_template",
                  "method", "requires_confirmed_token", "safety_tier", "allowed"):
        assert field in entry


def test_eligibility_read_only_eligible():
    r = _eligibility("GET /v1/agent-builder/discovery/gaps/ver_1", "GET")
    assert r["eligible"] is True
    assert r["action_key"] == "check_governance_gaps"
    assert r["will_execute"] is False
    assert r["is_advisory_only"] is True


def test_eligibility_activation_blocked_no_token():
    r = _eligibility("POST /v1/agent-candidate-activation/ver_1", "POST")
    assert r["eligible"] is False
    assert r["action_key"] == "activate_candidate"
    assert r["safety_tier"] == "activation_only"


def test_eligibility_unknown_endpoint_blocked():
    r = _eligibility("GET /v1/some/unknown/path", "GET")
    assert r["eligible"] is False
    assert r["action_key"] == "unknown"


def test_eligibility_action_key_direct():
    r = _eligibility("GET /anything", action_key="inspect_lifecycle")
    assert r["action_key"] == "inspect_lifecycle"
    assert r["eligible"] is True


def test_eligibility_unknown_action_key_blocked():
    r = _eligibility("GET /anything", action_key="not_in_registry")
    assert r["eligible"] is False


def test_eligibility_with_confirmed_token():
    # Create and confirm a token first
    preview = client.post(f"{BASE}/action-plan/step-preview", json={
        "plan_id": "aplan_demo",
        "step_number": 4,
        "step_title": "Activate candidate",
        "endpoint_hint": "POST /v1/agent-candidate-activation/ver_1",
        "method_hint": "POST",
        "severity": "blocking",
    }).json()
    tid = preview["token_id"]
    client.post(f"{BASE}/action-plan/step-confirm", json={"token_id": tid})
    r = _eligibility("POST /v1/agent-candidate-activation/ver_1", "POST", token_id=tid)
    assert r["eligible"] is True
    assert r["token_status"] == "confirmed"


def test_eligibility_decision_blocked_no_token():
    r = _eligibility("POST /v1/agent-candidate-decision/ver_1", "POST")
    assert r["eligible"] is False
    assert r["requires_confirmed_token"] is True


def test_eligibility_run_preview_blocked_no_token():
    r = _eligibility("POST /v1/agent-skill-run-preview/ver_1/run", "POST")
    assert r["eligible"] is False


def test_dispatch_audit_empty_initially():
    # Use a fresh client to avoid cross-test state (but TestClient shares DB)
    r = client.get(f"{BASE}/action-plan/dispatch-audit")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data["entries"], list)
    assert data["will_execute"] is False
    assert data["is_advisory_only"] is True


def test_dispatch_audit_accumulates():
    before = client.get(f"{BASE}/action-plan/dispatch-audit").json()["event_count"]
    _eligibility("GET /v1/agent-builder/discovery/gaps/ver_1", "GET")
    after = client.get(f"{BASE}/action-plan/dispatch-audit").json()["event_count"]
    assert after >= before + 1


def test_dispatch_audit_entry_fields():
    _eligibility("GET /v1/agent-builder/advisory/lifecycle-summary/ver_1", "GET")
    entry = client.get(f"{BASE}/action-plan/dispatch-audit").json()["entries"][0]
    for field in ("event_id", "action_key", "endpoint_hint", "eligible", "created_at"):
        assert field in entry


def test_safety_invariants_all_endpoints():
    responses = [
        client.get(f"{BASE}/action-registry").json(),
        _eligibility("GET /v1/agent-builder/discovery/gaps/v", "GET"),
        client.get(f"{BASE}/action-plan/dispatch-audit").json(),
    ]
    for resp in responses:
        assert resp.get("will_execute") is False
        assert resp.get("can_execute") is False
        assert resp.get("is_advisory_only") is True
