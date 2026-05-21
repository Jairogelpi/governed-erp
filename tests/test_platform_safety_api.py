from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


# ── POST /v1/platform/tenants ──────────────────────────────────────────────

def test_create_tenant_returns_201_or_200():
    resp = client.post("/v1/platform/tenants", json={"name": "API Tenant", "environment": "staging"})
    assert resp.status_code in (200, 201)
    body = resp.json()
    assert body["tenant_id"].startswith("tenant_")
    assert body["name"] == "API Tenant"
    assert body["environment"] == "staging"
    assert body["status"] == "active"
    assert body["secret_redaction_enforced"] is True


# ── GET /v1/platform/tenants/{tenant_id} ──────────────────────────────────

def test_get_tenant_ok():
    create_resp = client.post("/v1/platform/tenants", json={"name": "GetMe API", "environment": "staging"})
    tenant_id = create_resp.json()["tenant_id"]
    resp = client.get(f"/v1/platform/tenants/{tenant_id}")
    assert resp.status_code == 200
    assert resp.json()["tenant_id"] == tenant_id


def test_get_tenant_not_found():
    resp = client.get("/v1/platform/tenants/tenant_does_not_exist_xyz")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "tenant_not_found"


# ── POST /v1/platform/tenants/{tenant_id}/kill-switch ─────────────────────

def _create_tenant(name="KS API Tenant"):
    resp = client.post("/v1/platform/tenants", json={"name": name, "environment": "staging"})
    return resp.json()["tenant_id"]


def test_activate_kill_switch():
    tid = _create_tenant("KS Activate API")
    resp = client.post(f"/v1/platform/tenants/{tid}/kill-switch", json={
        "switch_name": "write_pilot_kill_switch",
        "action": "activate",
        "activated_by": {"type": "user", "id": "u1"},
        "reason": "API test activation",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["switch_name"] == "write_pilot_kill_switch"
    assert body["action"] == "activate"


def test_deactivate_kill_switch():
    tid = _create_tenant("KS Deactivate API")
    client.post(f"/v1/platform/tenants/{tid}/kill-switch", json={
        "switch_name": "runtime_execution_kill_switch",
        "action": "activate",
        "activated_by": {"type": "user", "id": "u1"},
        "reason": "on",
    })
    resp = client.post(f"/v1/platform/tenants/{tid}/kill-switch", json={
        "switch_name": "runtime_execution_kill_switch",
        "action": "deactivate",
        "activated_by": {"type": "user", "id": "u1"},
        "reason": "off",
    })
    assert resp.status_code == 200
    assert resp.json()["action"] == "deactivate"


def test_invalid_kill_switch_action_returns_400():
    tid = _create_tenant("KS Bad Action API")
    resp = client.post(f"/v1/platform/tenants/{tid}/kill-switch", json={
        "switch_name": "write_pilot_kill_switch",
        "action": "explode",
        "activated_by": {},
        "reason": "bad",
    })
    assert resp.status_code == 400


def test_invalid_switch_name_returns_400():
    tid = _create_tenant("KS Bad Name API")
    resp = client.post(f"/v1/platform/tenants/{tid}/kill-switch", json={
        "switch_name": "nonexistent_switch",
        "action": "activate",
        "activated_by": {},
        "reason": "bad",
    })
    assert resp.status_code == 400


# ── GET /v1/platform/tenants/{tenant_id}/safety-summary ───────────────────

def test_safety_summary():
    tid = _create_tenant("Summary API")
    resp = client.get(f"/v1/platform/tenants/{tid}/safety-summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == tid
    assert body["any_kill_switch_active"] is False
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False
    assert body["secret_redaction_enforced"] is True


def test_safety_summary_reflects_active_kill_switch():
    tid = _create_tenant("Summary KS API")
    client.post(f"/v1/platform/tenants/{tid}/kill-switch", json={
        "switch_name": "global_kill_switch",
        "action": "activate",
        "activated_by": {},
        "reason": "test",
    })
    resp = client.get(f"/v1/platform/tenants/{tid}/safety-summary")
    assert resp.status_code == 200
    assert resp.json()["any_kill_switch_active"] is True


# ── GET /v1/platform/tenants/{tenant_id}/audit-events ─────────────────────

def test_audit_events_empty():
    tid = _create_tenant("Audit Events API")
    resp = client.get(f"/v1/platform/tenants/{tid}/audit-events")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


# ── POST /v1/platform/tenants/{tenant_id}/audit-export ────────────────────

def test_generate_audit_export():
    tid = _create_tenant("Audit Export API")
    resp = client.post(f"/v1/platform/tenants/{tid}/audit-export", json={"filters": {}})
    assert resp.status_code == 200
    body = resp.json()
    assert body["tenant_id"] == tid
    assert body["export_type"] == "json"
    assert body["status"] == "completed"
    assert isinstance(body["result"], list)


def test_audit_export_not_found_tenant():
    resp = client.post("/v1/platform/tenants/tenant_no_exist_xyz/audit-export", json={"filters": {}})
    assert resp.status_code == 404


# ── GET /v1/platform/audit-exports/{export_id} ────────────────────────────

def test_get_audit_export_by_id():
    tid = _create_tenant("Export Get API")
    create_resp = client.post(f"/v1/platform/tenants/{tid}/audit-export", json={"filters": {}})
    export_id = create_resp.json()["export_id"]
    resp = client.get(f"/v1/platform/audit-exports/{export_id}")
    assert resp.status_code == 200
    assert resp.json()["export_id"] == export_id


def test_get_audit_export_not_found():
    resp = client.get("/v1/platform/audit-exports/export_nonexistent_xyz")
    assert resp.status_code == 404


# ── POST /v1/platform/policy/evaluate ─────────────────────────────────────

def test_policy_evaluate_allowed():
    resp = client.post("/v1/platform/policy/evaluate", json={
        "actor": {"role": "operator"},
        "action": "execute_real_read",
        "resource": "test_resource",
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is True
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False


def test_policy_evaluate_blocked_wrong_role():
    resp = client.post("/v1/platform/policy/evaluate", json={
        "actor": {"role": "operator"},
        "action": "approve_write_pilot",
        "resource": "test_resource",
    })
    assert resp.status_code == 200
    assert resp.json()["allowed"] is False


def test_policy_evaluate_with_tenant_and_kill_switch():
    tid = _create_tenant("Policy KS API")
    client.post(f"/v1/platform/tenants/{tid}/kill-switch", json={
        "switch_name": "global_kill_switch",
        "action": "activate",
        "activated_by": {},
        "reason": "test",
    })
    resp = client.post("/v1/platform/policy/evaluate", json={
        "actor": {"role": "admin"},
        "action": "execute_real_read",
        "resource": "x",
        "tenant_id": tid,
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["allowed"] is False
    assert "tenant_global_kill_switch" in body["kill_switches_active"]


# ── GET /v1/platform/runtime-safety ───────────────────────────────────────

def test_runtime_safety():
    resp = client.get("/v1/platform/runtime-safety")
    assert resp.status_code == 200
    body = resp.json()
    assert body["safety_level"] == "safe"
    assert body["allow_generic_real_odoo_writes"] is False
    assert body["allow_r3_r4_real_writes"] is False
    assert body["allow_r1_real_write_pilot"] is False
    assert body["secret_redaction_enforced"] is True
    assert isinstance(body["active_tenant_count"], int)
    assert isinstance(body["recent_write_pilot_runs"], int)
