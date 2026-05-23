"""
RC Demo Validation Script — ERPGuard v0.13.0-rc1

Runs the full operator rehearsal sequence against a live server and reports
pass/fail for each acceptance criterion.

Usage:
    python scripts/validate_rc_demo.py [--base-url http://127.0.0.1:8000]

Requires the server to be running. Does not start or stop the server.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib import request, error as url_error


def _get(base: str, path: str) -> tuple[int, Any]:
    try:
        with request.urlopen(f"{base}{path}", timeout=10) as r:
            return r.status, json.loads(r.read())
    except url_error.HTTPError as e:
        return e.code, {}
    except Exception as exc:
        return 0, {"_error": str(exc)}


def _post(base: str, path: str, payload: dict) -> tuple[int, Any]:
    data = json.dumps(payload).encode()
    req = request.Request(
        f"{base}{path}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except url_error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as exc:
        return 0, {"_error": str(exc)}


def run_validation(base_url: str) -> int:
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str = "") -> None:
        results.append((name, ok, detail))
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f" — {detail}" if detail else ""))

    print(f"\nERPGuard v0.13.0-rc1 — RC Validation ({base_url})\n{'='*60}")

    # Step 1 — demo dashboard
    print("\nStep 1: GET /demo")
    code, _ = _get(base_url, "/demo")
    check("GET /demo returns 200", code == 200, f"status={code}")

    # Step 2 — runbook
    print("\nStep 2: GET /v1/operator/demo-runbook")
    code, body = _get(base_url, "/v1/operator/demo-runbook")
    check("GET /demo-runbook returns 200", code == 200, f"status={code}")
    if code == 200:
        ops = body.get("operations", [])
        sprints = {op.get("sprint") for op in ops}
        check("Runbook has ≥15 operations", len(ops) >= 15, f"count={len(ops)}")
        check("Runbook covers Sprints 20-26", all(s in sprints for s in range(20, 27)),
              f"sprints={sorted(sprints)}")
        flags = {f.get("flag") for f in body.get("safety_flags", [])}
        check("ALLOW_GENERIC_REAL_ODOO_WRITES in flags", "ALLOW_GENERIC_REAL_ODOO_WRITES" in flags)

    # Step 3 — demo seed
    print("\nStep 3: POST /v1/operator/demo-seed")
    code, seed = _post(base_url, "/v1/operator/demo-seed", {"operator": "rc_validator"})
    check("POST /demo-seed returns 200", code == 200, f"status={code}")
    if code == 200:
        id_chain = ["session_id", "draft_id", "compiled_skill_id", "version_id", "run_id", "schedule_id"]
        chain_ok = all(seed.get(k) for k in id_chain)
        check("Full ID chain present", chain_ok, f"keys={[k for k in id_chain if seed.get(k)]}")
        check("erp_target contains fake-erp", "fake-erp" in seed.get("erp_target", ""),
              f"erp_target={seed.get('erp_target')}")
        check("Safety invariants list non-empty", len(seed.get("safety_invariants", [])) >= 9,
              f"count={len(seed.get('safety_invariants', []))}")

    # Step 4 — scheduler tick
    print("\nStep 4: POST /v1/skills/schedules/tick")
    code, tick = _post(base_url, "/v1/skills/schedules/tick", {})
    check("POST /tick returns 200", code == 200, f"status={code}")
    if code == 200:
        check("Tick report has due_count", "due_count" in tick, f"keys={list(tick.keys())}")
        check("Tick has no error field", "error" not in tick)

    # Step 5 — evidence pack
    print("\nStep 5: POST /v1/operator/evidence-packs")
    pack_payload = {
        "created_by": "rc_validator",
        "scenario_label": "RC v0.13.0-rc1 Validation",
        "seed_result": seed if code == 200 else {},
    }
    code, pack = _post(base_url, "/v1/operator/evidence-packs", pack_payload)
    check("POST /evidence-packs returns 200", code == 200, f"status={code}")
    pack_id = None
    if code == 200:
        pack_id = pack.get("pack_id", "")
        check("pack_id starts with evpack_", pack_id.startswith("evpack_"), f"pack_id={pack_id}")
        check("evidence_status=ready", pack.get("evidence_status") == "ready",
              f"status={pack.get('evidence_status')}")
        check("sprint_chain=20-26", pack.get("sprint_chain") == "20-26",
              f"chain={pack.get('sprint_chain')}")
        sc = pack.get("safety_checks", {})
        check("safety_checks.verdict=safe", sc.get("verdict") == "safe",
              f"verdict={sc.get('verdict')}")
        check("safety_checks.invariants_violated=0", sc.get("invariants_violated") == 0,
              f"violated={sc.get('invariants_violated')}")

    # Step 6 — safety report
    if pack_id:
        print(f"\nStep 6: GET /v1/operator/evidence-packs/{pack_id}/safety-report")
        code, safety = _get(base_url, f"/v1/operator/evidence-packs/{pack_id}/safety-report")
        check("GET /safety-report returns 200", code == 200, f"status={code}")
        if code == 200:
            check("verdict=safe", safety.get("verdict") == "safe", f"verdict={safety.get('verdict')}")
            check("invariants_enforced=12", safety.get("invariants_enforced") == 12,
                  f"enforced={safety.get('invariants_enforced')}")
            check("invariants_violated=0", safety.get("invariants_violated") == 0,
                  f"violated={safety.get('invariants_violated')}")
            sprints_covered = {s.get("sprint") for s in safety.get("sprint_coverage", [])}
            check("Sprint coverage 20-26", all(s in sprints_covered for s in range(20, 27)),
                  f"sprints={sorted(sprints_covered)}")

    # Step 7 — final report
    if pack_id:
        print(f"\nStep 7: GET /v1/operator/evidence-packs/{pack_id}/final-report")
        code, final = _get(base_url, f"/v1/operator/evidence-packs/{pack_id}/final-report")
        check("GET /final-report returns 200", code == 200, f"status={code}")
        if code == 200:
            check("safety_verdict=safe", final.get("safety_verdict") == "safe",
                  f"verdict={final.get('safety_verdict')}")
            check("invariants_violated=0", final.get("invariants_violated") == 0,
                  f"violated={final.get('invariants_violated')}")
            sprints = {s.get("sprint") for s in final.get("sprint_coverage", [])}
            check("Final report covers 20-26", all(s in sprints for s in range(20, 27)),
                  f"sprints={sorted(sprints)}")
            check("operation_count ≥ 15", final.get("operation_count", 0) >= 15,
                  f"count={final.get('operation_count')}")

    # Summary
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{'='*60}")
    print(f"Result: {passed} passed / {failed} failed")
    if failed == 0:
        print("RC ACCEPTED — v0.13.0-rc1 validation passed.")
    else:
        print("RC BLOCKED — fix failures before accepting.")
        for name, ok, detail in results:
            if not ok:
                print(f"  FAIL: {name} — {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate ERPGuard RC demo")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    sys.exit(run_validation(args.base_url))
