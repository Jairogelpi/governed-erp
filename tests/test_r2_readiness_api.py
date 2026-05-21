from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import SessionLocal, init_db
from erpguard.db.repositories import (
    create_skill, create_skill_version,
    create_r2_write_pilot_run, create_r2_write_pilot_evidence,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


def _make_run(status="blocked") -> str:
    session = SessionLocal()
    try:
        skill = create_skill(session, name="R11 API Skill", description=None)
        create_skill_version(session, skill.id, "1.0", "{}", "deterministic_browser", False)
        pre = {"target_model": "res.partner", "target_record_id": 1, "field_values": {"comment": "before"}}
        post = {"target_model": "res.partner", "target_record_id": 1, "field_values": {"comment": "before"}}
        run = create_r2_write_pilot_run(
            session,
            request_id=f"r2req_{skill.id[:10]}",
            skill_id=skill.id,
            status=status,
            executed_action="blocked_by_feature_flag",
            pre_snapshot_json=json.dumps(pre),
            post_snapshot_json=json.dumps(post),
            result_json="{}",
            policy_passed=False,
            allow_r2_real_write_pilot=False,
        )
        rollback = {
            "action": "re-write", "model": "res.partner", "record_id": 1,
            "restore_vals": {"comment": "before"},
            "odoo_call": "env['res.partner'].browse(1).write({'comment': 'before'})",
            "notes": "test",
        }
        create_r2_write_pilot_evidence(
            session,
            run_id=run.id, request_id=run.request_id, skill_id=skill.id,
            action_taken="blocked_by_feature_flag", target_model="res.partner", target_record_id="1",
            pre_snapshot_json=json.dumps(pre), post_snapshot_json=json.dumps(post),
            rollback_instructions_json=json.dumps(rollback),
            idempotency_key=f"r2_idem_{skill.id[:16]}", allow_r2_real_write_pilot=False,
        )
        return run.id
    finally:
        session.close()


# ── GET /evidence-review ───────────────────────────────────────────────────

def test_evidence_review_ok():
    run_id = _make_run()
    resp = client.get(f"/v1/product/r2-write-pilot/runs/{run_id}/evidence-review")
    assert resp.status_code == 200
    body = resp.json()
    assert body["review_id"].startswith("r2review_")
    assert body["run_id"] == run_id
    assert isinstance(body["fields_changed"], int)
    assert isinstance(body["drift_detected"], bool)
    assert body["safety_invariants"]["allow_generic_real_odoo_writes"] is False
    assert body["safety_invariants"]["allow_r3_r4_real_writes"] is False


def test_evidence_review_idempotent():
    run_id = _make_run()
    r1 = client.get(f"/v1/product/r2-write-pilot/runs/{run_id}/evidence-review").json()
    r2 = client.get(f"/v1/product/r2-write-pilot/runs/{run_id}/evidence-review").json()
    assert r1["review_id"] == r2["review_id"]


def test_evidence_review_run_not_found():
    resp = client.get("/v1/product/r2-write-pilot/runs/r2run_bad/evidence-review")
    assert resp.status_code == 404


# ── POST /rollback-rehearsal ───────────────────────────────────────────────

def test_rollback_rehearsal_ok():
    run_id = _make_run()
    resp = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/rollback-rehearsal")
    assert resp.status_code == 200
    body = resp.json()
    assert body["rehearsal_id"].startswith("r2reh_")
    assert body["run_id"] == run_id
    assert body["real_rollback_executed"] is False
    assert body["safety_invariants"]["can_execute_real_writes"] is False


def test_rollback_rehearsal_instructions_valid():
    run_id = _make_run()
    body = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/rollback-rehearsal").json()
    assert body["instructions_valid"] is True
    assert body["rehearsal_passed"] is True
    assert body["missing_fields"] == []
    assert len(body["dry_run_steps"]) >= 3


def test_rollback_rehearsal_idempotent():
    run_id = _make_run()
    r1 = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/rollback-rehearsal").json()
    r2 = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/rollback-rehearsal").json()
    assert r1["rehearsal_id"] == r2["rehearsal_id"]


def test_rollback_rehearsal_run_not_found():
    resp = client.post("/v1/product/r2-write-pilot/runs/r2run_bad/rollback-rehearsal")
    assert resp.status_code == 404


# ── GET /execution-report ──────────────────────────────────────────────────

def test_execution_report_ok():
    run_id = _make_run()
    resp = client.get(f"/v1/product/r2-write-pilot/runs/{run_id}/execution-report")
    assert resp.status_code == 200
    body = resp.json()
    assert body["report_id"].startswith("r2report_")
    assert body["run_id"] == run_id
    assert body["status"] == "completed"
    assert body["residual_risk_score"] == 0
    assert body["risk_level"] == "none"


def test_execution_report_idempotent():
    run_id = _make_run()
    r1 = client.get(f"/v1/product/r2-write-pilot/runs/{run_id}/execution-report").json()
    r2 = client.get(f"/v1/product/r2-write-pilot/runs/{run_id}/execution-report").json()
    assert r1["report_id"] == r2["report_id"]


def test_execution_report_run_not_found():
    resp = client.get("/v1/product/r2-write-pilot/runs/r2run_bad/execution-report")
    assert resp.status_code == 404


# ── POST /promotion-gate ───────────────────────────────────────────────────

def test_promotion_gate_blocked_without_review():
    run_id = _make_run()
    resp = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/promotion-gate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["gate_id"].startswith("r2gate_")
    assert body["blocked"] is True
    assert body["gate_status"] == "blocked"
    assert len(body["blocking_reasons"]) > 0


def test_promotion_gate_passed_after_full_review():
    run_id = _make_run(status="blocked")
    client.get(f"/v1/product/r2-write-pilot/runs/{run_id}/evidence-review")
    client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/rollback-rehearsal")
    client.get(f"/v1/product/r2-write-pilot/runs/{run_id}/execution-report")
    resp = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/promotion-gate")
    assert resp.status_code == 200
    body = resp.json()
    assert body["blocked"] is False
    assert body["gate_status"] == "passed"


def test_promotion_gate_invariants_always_safe():
    run_id = _make_run()
    body = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/promotion-gate").json()
    inv = body["safety_invariants"]
    assert inv["allow_generic_real_odoo_writes"] is False
    assert inv["allow_r3_r4_real_writes"] is False
    assert inv["can_execute_real_writes"] is False


def test_promotion_gate_generic_and_r3r4_checks_always_pass():
    run_id = _make_run()
    body = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/promotion-gate").json()
    checks = {c["name"]: c["passed"] for c in body["checks"]}
    assert checks["generic_writes_locked"] is True
    assert checks["r3_r4_writes_locked"] is True


def test_promotion_gate_idempotent():
    run_id = _make_run()
    r1 = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/promotion-gate").json()
    r2 = client.post(f"/v1/product/r2-write-pilot/runs/{run_id}/promotion-gate").json()
    assert r1["gate_id"] == r2["gate_id"]


def test_promotion_gate_run_not_found():
    resp = client.post("/v1/product/r2-write-pilot/runs/r2run_bad/promotion-gate")
    assert resp.status_code == 404
