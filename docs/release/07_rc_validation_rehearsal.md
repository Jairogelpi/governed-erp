# RC Validation Rehearsal

**Product:** ERPGuard — ERP Agent OS  
**Version:** v0.13.0-rc1  
**Sprint:** 27 — Release Candidate Validation & Demo Rehearsal  
**Date:** 2026-05-23  
**Evaluator role:** External operator (no internal knowledge assumed)

---

## Rehearsal Sequence

The following sequence is executed from a clean state, in order. Each step must
succeed before proceeding to the next. This is the same sequence a TFM evaluator
or production operator would follow.

---

### Step 0 — Clean state

```bash
python -m pytest -q
# Expected: 1162+ passed, 0 failed

git diff --check
# Expected: no output (clean)

python -m uvicorn apps.api.main:app --port 8000
# Expected: server starts without error
```

---

### Step 1 — Verify demo dashboard

```
GET http://127.0.0.1:8000/demo
```

**Expected:** HTTP 200. HTML contains:
- "ERP Agent OS" heading
- "Operator Evidence Pack" section
- `data-testid="demo-ep-seed"` button
- Sprint 26 label

---

### Step 2 — Verify operator runbook

```
GET http://127.0.0.1:8000/v1/operator/demo-runbook
```

**Expected:** HTTP 200. Body contains:
- `operation_count` ≥ 15
- Operations spanning `sprint` 20 through 26
- `kill_switches` list non-empty
- `safety_flags` with `ALLOW_GENERIC_REAL_ODOO_WRITES=false`

---

### Step 3 — Seed full demo scenario

```
POST http://127.0.0.1:8000/v1/operator/demo-seed
Content-Type: application/json
{"operator": "rc_evaluator"}
```

**Expected:** HTTP 200. Body contains:
- `session_id` — non-empty string
- `draft_id` — non-empty string
- `compiled_skill_id` — non-empty string
- `version_id` — non-empty string
- `run_id` — non-empty string
- `schedule_id` — non-empty string
- `safety_invariants` — list with ≥ 9 entries
- `erp_target` contains `fake-erp`

**ID chain verified:** session → draft → compiled_skill → version → run → schedule — all non-empty and distinct.

---

### Step 4 — Verify scheduler tick

```
POST http://127.0.0.1:8000/v1/skills/schedules/tick
Content-Type: application/json
{}
```

**Expected:** HTTP 200. Body contains:
- `due_count` ≥ 0
- `dispatched` or `skipped` list (tick is explicit — no autonomous execution)

**Key invariant:** This endpoint must be called manually. There is no autonomous background scheduler.

---

### Step 5 — Assemble evidence pack

```
POST http://127.0.0.1:8000/v1/operator/evidence-packs
Content-Type: application/json
{
  "created_by": "rc_evaluator",
  "scenario_label": "RC v0.13.0-rc1 Rehearsal",
  "seed_result": <body from Step 3>
}
```

**Expected:** HTTP 200. Body contains:
- `pack_id` starts with `evpack_`
- `evidence_status` = `ready`
- `sprint_chain` = `20-26`
- `safety_checks.verdict` = `safe`
- `safety_checks.invariants_violated` = 0

---

### Step 6 — Safety report

```
GET http://127.0.0.1:8000/v1/operator/evidence-packs/{pack_id}/safety-report
```

**Expected:** HTTP 200. Body contains:
- `verdict` = `safe`
- `invariants_enforced` = 12
- `invariants_violated` = 0
- `blocked_operations_count` ≥ 10
- Sprint coverage: sprints 20 through 26 all present

---

### Step 7 — Final report

```
GET http://127.0.0.1:8000/v1/operator/evidence-packs/{pack_id}/final-report
```

**Expected:** HTTP 200. Body contains:
- `safety_verdict` = `safe`
- `sprint_coverage` spans 20 through 26
- `invariants_enforced` = 12
- `invariants_violated` = 0
- `operation_count` ≥ 15
- `notes` list non-empty

---

## Rehearsal Result

All 7 steps passed. No gaps found. See `08_rc_gap_log.md` and `09_rc_acceptance_report.md`.
