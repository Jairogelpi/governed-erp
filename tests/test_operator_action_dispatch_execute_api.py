"""Sprint 45/46 — Confirmed action dispatcher API tests."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.models import ActionPlanStepToken
from erpguard.db.models import UISkillVersionRecord
from erpguard.db.session import SessionLocal, init_db

client = TestClient(app)
BASE = "/v1/operator-console/action-plan"


def _make_version(*, name: str = "formula-review", status: str = "candidate", is_active: bool = False) -> str:
    init_db()
    db = SessionLocal()
    try:
        version = UISkillVersionRecord(
            id=f"ver_{uuid.uuid4().hex[:16]}",
            skill_id=f"skill_{uuid.uuid4().hex[:8]}",
            compiled_skill_id=f"comp_{uuid.uuid4().hex[:8]}",
            name=name,
            status=status,
            steps_json='[{"type":"read","description":"Read formula order"}]',
            guard_names_json=json.dumps(["formula_guard"]),
            runtime_type="agent_advisory",
            promotion_readiness_json="{}",
            is_active=is_active,
        )
        db.add(version)
        db.commit()
        return version.id
    finally:
        db.close()


def _confirmed_token(endpoint_hint: str, method_hint: str = "GET") -> str:
    preview = client.post(f"{BASE}/step-preview", json={
        "plan_id": "aplan_api_dispatch",
        "step_number": 1,
        "step_title": "Dispatch read-only action",
        "endpoint_hint": endpoint_hint,
        "method_hint": method_hint,
        "severity": "blocking",
    })
    token_id = preview.json()["token_id"]
    client.post(f"{BASE}/step-confirm", json={"token_id": token_id})
    return token_id


def test_read_only_action_dispatches_correctly_via_api():
    _make_version(name="formula-search-target")
    token_id = _confirmed_token("GET /v1/agent-builder/discovery/search")
    body = {
        "plan_id": "aplan_api_dispatch",
        "step_number": 1,
        "action_key": "search_skills",
        "endpoint_hint": "POST https://evil.example/should-not-run",
        "method_hint": "POST",
        "token_id": token_id,
        "parameters": {"query": "formula"},
    }
    r = client.post(f"{BASE}/dispatch", json=body)
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "completed"
    assert data["dispatch_performed"] is True
    assert data["handler_type"] == "internal_read_only"
    assert data["is_advisory_only"] is False


def test_result_endpoint_recovers_dispatch_result():
    version_id = _make_version()
    token_id = _confirmed_token("GET /v1/agent-builder/discovery/recommendations/ver_1")
    r = client.post(f"{BASE}/dispatch", json={
        "plan_id": "aplan_api_dispatch",
        "step_number": 2,
        "action_key": "recommend_next_step",
        "endpoint_hint": "GET /ignored",
        "method_hint": "GET",
        "token_id": token_id,
        "version_id": version_id,
        "parameters": {"version_id": version_id},
    })
    dispatch_id = r.json()["dispatch_id"]
    get_r = client.get(f"{BASE}/dispatch-results/{dispatch_id}")
    assert get_r.status_code == 200
    assert get_r.json()["dispatch_id"] == dispatch_id


def test_dispatch_execution_audit_endpoint_returns_events():
    _make_version(name="formula-search-target")
    token_id = _confirmed_token("GET /v1/agent-builder/discovery/search")
    client.post(f"{BASE}/dispatch", json={
        "plan_id": "aplan_api_dispatch",
        "step_number": 1,
        "action_key": "search_skills",
        "endpoint_hint": "GET /ignored",
        "method_hint": "GET",
        "token_id": token_id,
        "parameters": {"query": "formula"},
    })
    r = client.get(f"{BASE}/dispatch-execution-audit")
    assert r.status_code == 200
    data = r.json()
    assert data["event_count"] >= 2
    assert "entries" in data


def test_dispatchable_actions_endpoint_returns_sprint46_allowlist():
    r = client.get(f"{BASE}/dispatchable-actions")
    assert r.status_code == 200
    actions = set(r.json()["actions"])
    # Read-only actions
    assert "check_governance_gaps" in actions
    assert "search_skills" in actions
    assert "reuse_suggestions" in actions
    assert "inspect_lifecycle" in actions
    assert "recommend_next_step" in actions
    assert "run_preview" in actions
    # Governance mutation actions
    assert "record_human_decision" in actions
    assert "create_activation_request" in actions
    assert "activate_candidate" in actions


def test_missing_token_blocks_via_api():
    r = client.post(f"{BASE}/dispatch", json={
        "plan_id": "aplan_api_dispatch",
        "step_number": 1,
        "action_key": "search_skills",
        "endpoint_hint": "GET /ignored",
        "method_hint": "GET",
        "token_id": "tok_missing",
        "parameters": {"query": "formula"},
    })
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"


def test_pending_token_blocks_via_api():
    preview = client.post(f"{BASE}/step-preview", json={
        "plan_id": "aplan_api_dispatch",
        "step_number": 1,
        "step_title": "Dispatch read-only action",
        "endpoint_hint": "GET /v1/agent-builder/discovery/search",
        "method_hint": "GET",
        "severity": "blocking",
    })
    token_id = preview.json()["token_id"]
    r = client.post(f"{BASE}/dispatch", json={
        "plan_id": "aplan_api_dispatch",
        "step_number": 1,
        "action_key": "search_skills",
        "endpoint_hint": "GET /ignored",
        "method_hint": "GET",
        "token_id": token_id,
        "parameters": {"query": "formula"},
    })
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"


def test_expired_token_blocks_via_api():
    token_id = _confirmed_token("GET /v1/agent-builder/discovery/search")
    init_db()
    db = SessionLocal()
    try:
        row = db.query(ActionPlanStepToken).filter(ActionPlanStepToken.id == token_id).first()
        row.status = "pending"
        row.confirmed_at = None
        row.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()
    finally:
        db.close()
    r = client.post(f"{BASE}/dispatch", json={
        "plan_id": "aplan_api_dispatch",
        "step_number": 1,
        "action_key": "search_skills",
        "endpoint_hint": "GET /ignored",
        "method_hint": "GET",
        "token_id": token_id,
        "parameters": {"query": "formula"},
    })
    assert r.status_code == 200
    assert r.json()["status"] == "blocked"


def test_activate_candidate_without_version_blocks_via_api():
    """activate_candidate with no version_id must still block (version not found)."""
    token_id = _confirmed_token("POST /v1/agent-candidate-activation/ver_1", "POST")
    r = client.post(f"{BASE}/dispatch", json={
        "plan_id": "aplan_api_dispatch",
        "step_number": 1,
        "action_key": "activate_candidate",
        "endpoint_hint": "POST /ignored",
        "method_hint": "POST",
        "token_id": token_id,
        "parameters": {},
    })
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "blocked"
    assert data["handler_type"] == "internal_governance_mutation"
