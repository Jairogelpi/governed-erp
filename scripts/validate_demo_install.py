"""Spec 95 (Phase 22) Sec 31.3 -- clean-install acceptance script.

Drives the real, current golden path against a running ERPGuard server
purely over HTTP (no monkeypatching, no direct DB session, no test-only
helpers) -- the same discipline `scripts/validate_rc_demo.py` and
`scripts/check_release_install.py` already use, extended to the modern
Fake-connector pipeline (process registration -> fake event generation ->
variant discovery -> candidate -> replay -> freeze -> Proof of Improvement
-> compile -> approve -> execution permit) plus the token-bootstrap flow
Spec 94 added (`POST /internal/dev-tokens`).

Usage:
    docker compose -f docker-compose.demo.yml up --build -d
    python scripts/validate_demo_install.py [--base-url http://127.0.0.1:8000]

Requires the server to already be running with
`ERPGUARD_INTERNAL_SURFACES=true` (docker-compose.demo.yml sets this) --
does not start or stop the server itself.

IMPORTANT, read before trusting a green run: the decision-to-outcome
pillar (Spec 92 -- opportunity -> recommendation -> canary -> outcome ->
evidence bundle) is INTENTIONALLY NOT exercised here. Every path to create
a `MarginOpportunity` in this codebase starts from an `AnalyticalSnapshot`
(`POST /v1/decision-intelligence/snapshots`), which performs a real,
bounded Odoo read -- there is currently no Fake-ERP/fixture equivalent
exposed through the public API. That is a real, undocumented-until-now
architectural gap, not an oversight in this script: see the "Known gaps"
section this phase's docs record it under. This script reports that
pillar as SKIPPED with the reason printed, never as a silent or fabricated
PASS, and does not fail the overall exit code on it alone.
"""
from __future__ import annotations

import argparse
import json
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib import error as url_error
from urllib import request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Reusing the real fixture builder (pure function, no DB/monkeypatching)
# rather than hand-rolling an OCEL document keeps this script honest and
# self-updating if the canonical SalesOrder shape ever changes -- this is
# the exact function `tests/test_phase14_skill_compiler.py` and friends
# use to seed a Proof-of-Improvement-eligible case.
from erpguard.domain.events.fake_generator import build_fake_quote_to_order_ocel  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PROCESS_YAML = (ROOT / "policies" / "processes" / "quote_to_order_v1.yaml").read_text(encoding="utf-8")


def _get(base: str, path: str, headers: dict | None = None) -> tuple[int, Any]:
    req = request.Request(f"{base}{path}", headers=headers or {})
    try:
        with request.urlopen(req, timeout=15) as r:
            return r.status, json.loads(r.read())
    except url_error.HTTPError as e:
        try:
            return e.code, json.loads(e.read())
        except Exception:
            return e.code, {}
    except Exception as exc:
        return 0, {"_error": str(exc)}


def _post(base: str, path: str, payload: dict, headers: dict | None = None) -> tuple[int, Any]:
    data = json.dumps(payload).encode()
    all_headers = {"Content-Type": "application/json", **(headers or {})}
    req = request.Request(f"{base}{path}", data=data, headers=all_headers, method="POST")
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

    def check(name: str, ok: bool, detail: str = "") -> bool:
        results.append((name, ok, detail))
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {name}" + (f" -- {detail}" if detail else ""))
        return ok

    print(f"\nERPGuard clean-install validation ({base_url})\n{'=' * 60}")
    run_id = uuid.uuid4().hex[:10]
    tenant_id = f"demo-install-{run_id}"

    # Step 1 -- health
    print("\nStep 1: GET /v1/health")
    code, _ = _get(base_url, "/v1/health")
    if not check("GET /v1/health returns 200", code == 200, f"status={code}"):
        print("\nServer unreachable -- aborting remaining checks.")
        return 1

    # Step 2 -- dev-token bootstrap (Spec 94)
    print("\nStep 2: POST /internal/dev-tokens")
    code, token_body = _post(
        base_url, "/internal/dev-tokens",
        {"tenant_id": tenant_id, "role_name": "admin", "display_name": "Clean-install validator"},
    )
    if not check("POST /internal/dev-tokens returns 201", code == 201, f"status={code}"):
        print("\nCannot obtain a session token (is ERPGUARD_INTERNAL_SURFACES=true?) -- aborting.")
        return 1
    headers = {"Authorization": f"Bearer {token_body['token']}"}

    # Step 3 -- register the baseline Quote-to-Order process
    print("\nStep 3: POST /v1/processes (baseline)")
    code, _ = _post(base_url, "/v1/processes", {"yaml": PROCESS_YAML}, headers)
    check("POST /v1/processes returns 201 or 409 (already registered)", code in (201, 409), f"status={code}")

    # Step 4 -- seed a Fake ERP case matching the Quote-to-Order fixture
    # vocabulary. `POST /v1/events/fake-generate`
    # (`erpguard.domain.events.fake_generator.build_fake_ocel`) used to emit
    # `sales.order.created`/`sales.order.reviewed`, which did not match
    # `quote_to_order_v1.yaml`'s declared event vocabulary -- that has since
    # been fixed (see CHANGELOG.md). This script still uses
    # `build_fake_quote_to_order_ocel` rather than the `fake-generate`
    # endpoint for an independent reason: only the former attaches a real
    # `SalesOrder` object payload (`ocel:ovmap`) with formula/margin data,
    # which the candidate-evidence and Proof-of-Improvement policy checks
    # further down (`evaluate_formula_guard_policy`) need. `fake-generate`'s
    # fixture is intentionally minimal (just enough to make variant
    # discovery find the happy-path variant for the web app's "Ingerir
    # eventos de ejemplo" button) and does not carry that payload.
    print("\nStep 4: POST /v1/events/ocel/import (Quote-to-Order vocabulary)")
    object_key = f"so-demo-install-{run_id}"
    ocel_document = build_fake_quote_to_order_ocel(tenant_id=tenant_id, object_key=object_key, formula_valid=True)
    code, _ = _post(base_url, "/v1/events/ocel/import", {"document": ocel_document, "source": "validate_demo_install"}, headers)
    check("POST /v1/events/ocel/import returns 201", code == 201, f"status={code}")

    # Step 5 -- variant discovery
    print("\nStep 5: GET /v1/variants?object_type=sales_order")
    code, variants = _get(base_url, "/v1/variants?object_type=sales_order", headers)
    variants_ok = check("GET /v1/variants returns 201/200 with at least one variant", code == 200 and len(variants) > 0, f"status={code} count={len(variants) if code == 200 else 'n/a'}")
    if not variants_ok:
        print("\nNo variants discovered -- cannot continue candidate/replay/proof chain.")
        _print_summary(results)
        return 1
    case_id = variants[0]["case_ids"][0]

    # Step 6-7 -- process candidate: create, submit
    print("\nStep 6-7: POST /v1/process-candidates -> submit")
    candidate_version = f"1.1.0-demo-{run_id}"
    code, candidate = _post(
        base_url, "/v1/process-candidates", headers=headers, payload={
            "process_key": "quote_to_order", "base_version": "1.0.0", "candidate_version": candidate_version,
            "changes": {"add_metric": {"name": "extra_metric", "kind": "duration", "start_event": "sales.quote.created", "end_event": "sales.order.created"}},
            "evidence_refs": [f"case:{case_id}"],
        },
    )
    if not check("POST /v1/process-candidates returns 201", code == 201, f"status={code} body={candidate}"):
        _print_summary(results)
        return 1
    candidate_id = candidate["id"]
    code, _ = _post(base_url, f"/v1/process-candidates/{candidate_id}/submit", {}, headers)
    check("POST .../submit returns 200", code == 200, f"status={code}")

    # Step 8 -- register the candidate's process version
    print("\nStep 8: POST /v1/processes (candidate version)")
    candidate_yaml = PROCESS_YAML.replace("version: 1.0.0", f"version: {candidate_version}")
    code, _ = _post(base_url, "/v1/processes", {"yaml": candidate_yaml}, headers)
    check("POST /v1/processes (candidate) returns 201", code == 201, f"status={code}")

    # Step 9-10 -- baseline and candidate replays
    print("\nStep 9-10: replays (baseline, candidate)")
    code, baseline_replay = _post(
        base_url, "/v1/processes/quote_to_order/versions/1.0.0/replays", {"object_type": "sales_order"}, headers
    )
    check("Baseline replay returns 201", code == 201, f"status={code}")
    code, candidate_replay = _post(
        base_url, f"/v1/processes/quote_to_order/versions/{candidate_version}/replays", {"object_type": "sales_order"}, headers
    )
    if not check("Candidate replay returns 201", code == 201, f"status={code} body={candidate_replay}"):
        _print_summary(results)
        return 1

    # Step 11-12 -- freeze both
    print("\nStep 11-12: freeze both replays")
    code, _ = _post(base_url, f"/v1/replays/{baseline_replay['id']}/freeze", {}, headers)
    check("Freeze baseline returns 200", code == 200, f"status={code}")
    code, _ = _post(base_url, f"/v1/replays/{candidate_replay['id']}/freeze", {}, headers)
    check("Freeze candidate returns 200", code == 200, f"status={code}")

    # Step 13 -- Proof of Improvement
    print("\nStep 13: POST /v1/replays/{id}/proofs")
    code, proof = _post(
        base_url, f"/v1/replays/{candidate_replay['id']}/proofs",
        {"baseline_replay_id": baseline_replay["id"], "benchmark_version": "erpriskbench-1.0.0"}, headers,
    )
    proof_ok = check("Proof generated (201)", code == 201, f"status={code} body={proof}")
    if proof_ok:
        check("Proof recommendation is eligible_for_shadow", proof.get("recommendation") == "eligible_for_shadow", f"recommendation={proof.get('recommendation')}")

    # Step 14 -- compile skill
    print("\nStep 14: POST /v1/process-candidates/{id}/compile")
    code, package = _post(
        base_url, f"/v1/process-candidates/{candidate_id}/compile",
        {"connector_id": "fake", "workflow_steps": [{"step_name": "read_order", "capability": "sales.order.read"}]}, headers,
    )
    if not check("Skill compiled (201)", code == 201, f"status={code} body={package}"):
        _print_summary(results)
        return 1
    skill_id = package["id"]

    # Step 15 -- approve skill
    print("\nStep 15: POST /v1/skills/{id}/versions/{v}/approve")
    code, _ = _post(base_url, f"/v1/skills/{skill_id}/versions/{candidate_version}/approve", {}, headers)
    check("Skill approved (200)", code == 200, f"status={code}")

    # Step 16 -- Fake connection
    print("\nStep 16: POST /v1/connections (fake)")
    code, connection = _post(
        base_url, "/v1/connections", {
            "name": f"demo-install-conn-{run_id}", "connector_type": "fake",
            "endpoint": "https://fake.example.test", "auth_type": "api_key", "secret": "fake-secret-value",
        }, headers,
    )
    if not check("Fake connection created (201)", code == 201, f"status={code} body={connection}"):
        _print_summary(results)
        return 1

    # Step 17-19 -- plan, approve, execute
    print("\nStep 17-19: execution permit plan -> approve -> execute")
    code, run = _post(
        base_url, "/v1/runs/plan", {
            "connection_id": connection["id"], "skill_package_id": skill_id,
            "capability": "sales.order.read", "idempotency_key": f"demo-install-{run_id}",
        }, headers,
    )
    if not check("Run planned (201)", code == 201, f"status={code} body={run}"):
        _print_summary(results)
        return 1
    code, approval = _post(base_url, "/v1/approvals", {"scope": "run:execute"}, headers)
    check("Approval created (201)", code == 201, f"status={code}")
    code, _ = _post(
        base_url, f"/v1/runs/{run['id']}/approve",
        {"approval_ids": [approval["id"]], "ttl_seconds": 900}, headers,
    )
    check("Run approved (200)", code == 200, f"status={code}")
    code, executed = _post(base_url, f"/v1/runs/{run['id']}/execute", {}, headers)
    execute_ok = check("Run executed (200)", code == 200, f"status={code} body={executed}")
    if execute_ok:
        # `sales.order.read` is read-only on the Fake connector, so
        # "blocked / execution_not_enabled" is the CORRECT, safe outcome
        # here -- not a failure. A generic write capability succeeding
        # unexpectedly would be the actual regression to catch.
        status_value = executed.get("status")
        check(
            "Execution runtime returns a safe terminal status (blocked or succeeded)",
            status_value in ("blocked", "succeeded"), f"status_value={status_value}",
        )

    # Decision-to-outcome pillar: documented, non-blocking gap.
    print("\nDecision-to-outcome pillar (Spec 92): SKIPPED")
    print(
        "  Every path to a MarginOpportunity requires a real Odoo-derived\n"
        "  AnalyticalSnapshot (POST /v1/decision-intelligence/snapshots) --\n"
        "  there is no Fake-ERP/fixture equivalent exposed through the\n"
        "  public API today. Recommendation/canary/outcome/evidence-bundle\n"
        "  coverage against this compose stack is therefore not currently\n"
        "  possible without live Odoo credentials. See the capability\n"
        "  reality matrix and this phase's memory draft, section\n"
        "  'Limitations and conclusions'."
    )

    return _print_summary(results)


def _print_summary(results: list[tuple[str, bool, str]]) -> int:
    passed = sum(1 for _, ok, _ in results if ok)
    failed = sum(1 for _, ok, _ in results if not ok)
    print(f"\n{'=' * 60}")
    print(f"Result: {passed} passed / {failed} failed")
    if failed == 0:
        print("CLEAN INSTALL ACCEPTED (Fake ERP path). Decision-to-outcome pillar not exercised -- see note above.")
    else:
        print("CLEAN INSTALL BLOCKED -- fix failures before accepting.")
        for name, ok, detail in results:
            if not ok:
                print(f"  FAIL: {name} -- {detail}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate an ERPGuard clean install (Spec 95 Sec 31.3)")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    sys.exit(run_validation(args.base_url))
