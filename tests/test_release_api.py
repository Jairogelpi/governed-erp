from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db
from erpguard.version import __version__

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


# ── GET /v1/release/health ─────────────────────────────────────────────────

def test_health_ok():
    resp = client.get("/v1/release/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["version"] == __version__
    assert body["db_accessible"] is True
    assert body["safety_boundaries_locked"] is True


def test_health_safety_boundaries_all_false():
    body = client.get("/v1/release/health").json()
    sb = body["safety_boundaries"]
    assert sb["ALLOW_GENERIC_REAL_ODOO_WRITES"] is False
    assert sb["ALLOW_R3_R4_REAL_WRITES"] is False
    assert sb["can_execute_real_writes"] is False
    assert sb["ALLOW_R2_REAL_WRITE_PILOT"] is False


# ── GET /v1/release/readiness-report ──────────────────────────────────────

def test_readiness_report():
    resp = client.get("/v1/release/readiness-report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["release_version"] == __version__
    assert body["status"] in ("ready", "partial", "not_ready")
    assert body["readiness_score"] >= 0
    assert len(body["checks"]) >= 8
    assert len(body["sprint_chain"]) == 13


def test_readiness_report_checks_have_required_names():
    body = client.get("/v1/release/readiness-report").json()
    check_names = {c["name"] for c in body["checks"]}
    assert "generic_writes_locked" in check_names
    assert "r3_r4_writes_locked" in check_names
    assert "safety_flags_all_false" in check_names


def test_readiness_report_blocked_operations_listed():
    body = client.get("/v1/release/readiness-report").json()
    blocked = body["blocked_operations"]
    assert len(blocked) >= 5
    assert any("action_confirm" in op for op in blocked)


# ── POST /v1/release/demo-seed ────────────────────────────────────────────

def test_demo_seed():
    resp = client.post("/v1/release/demo-seed")
    assert resp.status_code == 200
    body = resp.json()
    assert body["seeded"] is True
    assert body["tenant_id"].startswith("tenant_")
    assert body["skill_id"].startswith("skill_")
    assert body["operator_session_id"].startswith("opsession_")
    assert body["operator_session_step"] == "awaiting_connection"


def test_demo_seed_safety_invariants():
    body = client.post("/v1/release/demo-seed").json()
    inv = body["safety_invariants"]
    assert inv["can_execute_real_writes"] is False
    assert inv["allow_generic_real_odoo_writes"] is False
    assert inv["allow_r3_r4_real_writes"] is False


def test_demo_seed_provides_next_steps():
    body = client.post("/v1/release/demo-seed").json()
    assert len(body["next_steps"]) >= 3


# ── POST /v1/release/operator-smoke ───────────────────────────────────────

def test_operator_smoke():
    resp = client.post("/v1/release/operator-smoke")
    assert resp.status_code == 200
    body = resp.json()
    assert body["smoke_status"] in ("passed", "partial", "failed")
    assert body["checks_total"] == 7
    assert isinstance(body["checks_passed"], int)


def test_operator_smoke_safety_invariants():
    body = client.post("/v1/release/operator-smoke").json()
    inv = body["safety_invariants"]
    assert inv["can_execute_real_writes"] is False
    assert inv["allow_generic_real_odoo_writes"] is False
    assert inv["allow_r3_r4_real_writes"] is False


def test_operator_smoke_safety_boundaries_check_passes():
    body = client.post("/v1/release/operator-smoke").json()
    check = next(c for c in body["checks"] if c["name"] == "safety_boundaries")
    assert check["passed"] is True


def test_operator_smoke_r2_flag_check_passes():
    body = client.post("/v1/release/operator-smoke").json()
    check = next(c for c in body["checks"] if c["name"] == "r2_pilot_flag_default_off")
    assert check["passed"] is True


# ── GET /v1/release/safety-boundaries ─────────────────────────────────────

def test_safety_boundaries():
    resp = client.get("/v1/release/safety-boundaries")
    assert resp.status_code == 200
    body = resp.json()
    assert body["safety_boundaries"]["ALLOW_GENERIC_REAL_ODOO_WRITES"] is False
    assert body["safety_boundaries"]["ALLOW_R3_R4_REAL_WRITES"] is False
    assert "mail.message" in body["allowed_r1_models"]
    assert "res.partner" in body["allowed_r2_models"]
    assert "comment" in body["allowed_r2_fields"]
    assert "website" in body["allowed_r2_fields"]
    assert "staging" in body["allowed_environments"]
    assert len(body["blocked_operations"]) >= 5
    assert len(body["notes"]) >= 5
