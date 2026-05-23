"""
RC Validation Contract — ERPGuard v0.13.0-rc1

Validates all acceptance criteria from docs/release/09_rc_acceptance_report.md
without executing a full end-to-end chain. Each criterion is tested in isolation.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


# ── Criterion 1: /demo returns 200 ────────────────────────────────────────────

def test_demo_returns_200():
    r = client.get("/demo")
    assert r.status_code == 200


def test_demo_has_operator_evidence_pack_section():
    r = client.get("/demo")
    assert "Operator Evidence Pack" in r.text


def test_demo_has_sprint_26_section():
    r = client.get("/demo")
    assert "Sprint 26" in r.text


# ── Criterion 2: demo-runbook covers Sprints 20–26 ───────────────────────────

def test_runbook_returns_200():
    r = client.get("/v1/operator/demo-runbook")
    assert r.status_code == 200


def test_runbook_has_sufficient_operations():
    body = client.get("/v1/operator/demo-runbook").json()
    assert body["operation_count"] >= 15
    assert len(body["operations"]) >= 15


def test_runbook_covers_all_sprints():
    body = client.get("/v1/operator/demo-runbook").json()
    sprint_nums = {op["sprint"] for op in body["operations"]}
    for s in range(20, 27):
        assert s in sprint_nums, f"Sprint {s} missing from runbook"


def test_runbook_safety_flags_include_write_gate():
    body = client.get("/v1/operator/demo-runbook").json()
    flags = {f["flag"] for f in body["safety_flags"]}
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES" in flags


def test_runbook_kill_switches_present():
    body = client.get("/v1/operator/demo-runbook").json()
    assert len(body["kill_switches"]) >= 2


# ── Criterion 3: demo-seed succeeds ──────────────────────────────────────────

def test_demo_seed_returns_200():
    r = client.post("/v1/operator/demo-seed", json={"operator": "rc_contract_test"})
    assert r.status_code == 200


def test_demo_seed_full_id_chain():
    body = client.post("/v1/operator/demo-seed", json={}).json()
    for key in ["session_id", "draft_id", "compiled_skill_id", "version_id", "run_id", "schedule_id"]:
        assert body.get(key), f"Missing or empty: {key}"


def test_demo_seed_erp_target_is_fake():
    body = client.post("/v1/operator/demo-seed", json={}).json()
    assert "fake-erp" in body.get("erp_target", "")


def test_demo_seed_safety_invariants():
    body = client.post("/v1/operator/demo-seed", json={}).json()
    assert len(body.get("safety_invariants", [])) >= 9
    joined = " ".join(body["safety_invariants"])
    assert "no_llm" in joined.lower() or "llm" in joined.lower()
    assert "no_background" in joined.lower() or "scheduler" in joined.lower()


# ── Criterion 4: scheduler tick is explicit ───────────────────────────────────

def test_scheduler_tick_returns_200():
    r = client.post("/v1/skills/schedules/tick", json={})
    assert r.status_code == 200


def test_scheduler_tick_has_due_count():
    body = client.post("/v1/skills/schedules/tick", json={}).json()
    assert "due_count" in body


def test_scheduler_tick_has_no_error_key():
    body = client.post("/v1/skills/schedules/tick", json={}).json()
    assert "error" not in body


# ── Criterion 5: evidence pack assembled ─────────────────────────────────────

def test_evidence_pack_assembled():
    r = client.post("/v1/operator/evidence-packs", json={"created_by": "rc_contract"})
    assert r.status_code == 200
    body = r.json()
    assert body["pack_id"].startswith("evpack_")
    assert body["evidence_status"] == "ready"
    assert body["sprint_chain"] == "20-26"


def test_evidence_pack_with_seed_result():
    seed = client.post("/v1/operator/demo-seed", json={}).json()
    r = client.post("/v1/operator/evidence-packs", json={
        "created_by": "rc_contract",
        "seed_result": seed,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["seed_result"].get("version_id") == seed.get("version_id")


# ── Criterion 6: safety report verdict = safe ────────────────────────────────

def test_safety_report_verdict_safe():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}/safety-report").json()
    assert body["verdict"] == "safe"


def test_safety_report_invariants_violated_zero():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}/safety-report").json()
    assert body["invariants_violated"] == 0


def test_safety_report_invariants_enforced_twelve():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}/safety-report").json()
    assert body["invariants_enforced"] == 12


# ── Criterion 7: final report covers Sprints 20–26 ───────────────────────────

def test_final_report_verdict_safe():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}/final-report").json()
    assert body["safety_verdict"] == "safe"


def test_final_report_sprint_coverage():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}/final-report").json()
    sprint_nums = {s["sprint"] for s in body["sprint_coverage"]}
    for s in range(20, 27):
        assert s in sprint_nums, f"Sprint {s} missing from final report"


def test_final_report_operation_count():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}/final-report").json()
    assert body["operation_count"] >= 15


# ── Criterion: no autonomous background scheduler ─────────────────────────────

def test_tick_endpoint_exists_and_is_manual():
    r = client.post("/v1/skills/schedules/tick", json={})
    assert r.status_code == 200
    body = r.json()
    # Manual tick always returns a structured report — never a daemon handle
    assert "due_count" in body
    assert "dispatched" in body
    assert "skipped" in body
    assert "failed" in body


# ── Criterion: no real ERP browser automation ────────────────────────────────

def test_safety_report_blocks_real_odoo():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}/safety-report").json()
    blocked = " ".join(body.get("blocked_operations", [])).lower()
    assert "real odoo" in blocked or "odoo" in blocked


# ── Criterion: no LLM replay ─────────────────────────────────────────────────

def test_safety_report_blocks_llm_replay():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    body = client.get(f"/v1/operator/evidence-packs/{pack_id}/safety-report").json()
    inv_ids = {i["id"] for i in body.get("invariants", [])}
    assert "no_llm_replay" in inv_ids
