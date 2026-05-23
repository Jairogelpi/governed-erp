"""
RC Demo Rehearsal — Full End-to-End Sequence

Runs the complete 7-step operator rehearsal from docs/release/07_rc_validation_rehearsal.md
as a single integration test chain. Each step depends on the previous one.
"""
from __future__ import annotations

from fastapi.testclient import TestClient
from apps.api.main import app

client = TestClient(app)


def test_full_rehearsal_sequence():
    """Runs all 7 rehearsal steps in order and asserts each criterion."""

    # Step 1 — demo dashboard
    r = client.get("/demo")
    assert r.status_code == 200, "Step 1: /demo must return 200"
    assert "Operator Evidence Pack" in r.text, "Step 1: missing Operator Evidence Pack section"

    # Step 2 — runbook
    r = client.get("/v1/operator/demo-runbook")
    assert r.status_code == 200, "Step 2: /demo-runbook must return 200"
    runbook = r.json()
    sprint_nums = {op["sprint"] for op in runbook["operations"]}
    assert all(s in sprint_nums for s in range(20, 27)), f"Step 2: missing sprints in runbook, got {sprint_nums}"
    assert runbook["operation_count"] >= 15, "Step 2: operation_count must be ≥ 15"

    # Step 3 — demo seed
    r = client.post("/v1/operator/demo-seed", json={"operator": "rehearsal_evaluator"})
    assert r.status_code == 200, "Step 3: /demo-seed must return 200"
    seed = r.json()
    for key in ["session_id", "draft_id", "compiled_skill_id", "version_id", "run_id", "schedule_id"]:
        assert seed.get(key), f"Step 3: ID chain missing key '{key}'"
    assert "fake-erp" in seed.get("erp_target", ""), "Step 3: erp_target must contain fake-erp"
    assert len(seed.get("safety_invariants", [])) >= 9, "Step 3: safety_invariants must have ≥ 9 entries"

    # Step 4 — scheduler tick
    r = client.post("/v1/skills/schedules/tick", json={})
    assert r.status_code == 200, "Step 4: /tick must return 200"
    tick = r.json()
    assert "due_count" in tick, "Step 4: tick report must have due_count"
    assert "error" not in tick, "Step 4: tick report must not have error key"

    # Step 5 — evidence pack
    r = client.post("/v1/operator/evidence-packs", json={
        "created_by": "rehearsal_evaluator",
        "scenario_label": "RC v0.13.0-rc1 Rehearsal",
        "seed_result": seed,
    })
    assert r.status_code == 200, "Step 5: /evidence-packs must return 200"
    pack = r.json()
    pack_id = pack["pack_id"]
    assert pack_id.startswith("evpack_"), f"Step 5: pack_id format wrong: {pack_id}"
    assert pack["evidence_status"] == "ready", f"Step 5: evidence_status={pack['evidence_status']}"
    assert pack["sprint_chain"] == "20-26", f"Step 5: sprint_chain={pack['sprint_chain']}"
    sc = pack.get("safety_checks", {})
    assert sc.get("verdict") == "safe", f"Step 5: safety_checks.verdict={sc.get('verdict')}"
    assert sc.get("invariants_violated") == 0, f"Step 5: violated={sc.get('invariants_violated')}"

    # Step 6 — safety report
    r = client.get(f"/v1/operator/evidence-packs/{pack_id}/safety-report")
    assert r.status_code == 200, "Step 6: /safety-report must return 200"
    safety = r.json()
    assert safety["verdict"] == "safe", f"Step 6: verdict={safety['verdict']}"
    assert safety["invariants_enforced"] == 12, f"Step 6: enforced={safety['invariants_enforced']}"
    assert safety["invariants_violated"] == 0, f"Step 6: violated={safety['invariants_violated']}"
    sprint_cov = {s["sprint"] for s in safety.get("sprint_coverage", [])}
    assert all(s in sprint_cov for s in range(20, 27)), f"Step 6: sprint coverage={sprint_cov}"

    # Step 7 — final report
    r = client.get(f"/v1/operator/evidence-packs/{pack_id}/final-report")
    assert r.status_code == 200, "Step 7: /final-report must return 200"
    final = r.json()
    assert final["safety_verdict"] == "safe", f"Step 7: safety_verdict={final['safety_verdict']}"
    assert final["invariants_violated"] == 0, f"Step 7: invariants_violated={final['invariants_violated']}"
    sprint_cov = {s["sprint"] for s in final.get("sprint_coverage", [])}
    assert all(s in sprint_cov for s in range(20, 27)), f"Step 7: sprint_coverage={sprint_cov}"
    assert final["operation_count"] >= 15, f"Step 7: operation_count={final['operation_count']}"
    assert final.get("notes"), "Step 7: final report must have notes"


def test_rehearsal_seed_result_propagates_to_final_report():
    seed = client.post("/v1/operator/demo-seed", json={}).json()
    pack_id = client.post("/v1/operator/evidence-packs", json={"seed_result": seed}).json()["pack_id"]
    final = client.get(f"/v1/operator/evidence-packs/{pack_id}/final-report").json()
    notes_text = " ".join(final.get("notes", []))
    assert seed["version_id"] in notes_text or seed["run_id"] in notes_text


def test_rehearsal_safety_invariant_no_llm_present():
    pack_id = client.post("/v1/operator/evidence-packs", json={}).json()["pack_id"]
    safety = client.get(f"/v1/operator/evidence-packs/{pack_id}/safety-report").json()
    inv_ids = {i["id"] for i in safety.get("invariants", [])}
    assert "no_llm_replay" in inv_ids
    assert "fake_erp_only" in inv_ids
    assert "no_background_scheduler" in inv_ids


def test_rehearsal_tick_returns_structured_report():
    tick = client.post("/v1/skills/schedules/tick", json={}).json()
    assert isinstance(tick.get("dispatched"), list)
    assert isinstance(tick.get("skipped"), list)
    assert isinstance(tick.get("failed"), list)
    assert isinstance(tick.get("due_count"), int)
