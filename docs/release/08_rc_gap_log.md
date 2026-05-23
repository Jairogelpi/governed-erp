# RC Gap Log

**Product:** ERPGuard — ERP Agent OS  
**Version:** v0.13.0-rc1  
**Sprint:** 27 — Release Candidate Validation & Demo Rehearsal  
**Date:** 2026-05-23

---

## Summary

No blocking gaps found during the Sprint 27 rehearsal.

All 7 validation steps passed. The full ID chain (session → draft → compiled →
version → run → schedule) was verified end-to-end. The safety report returned
`verdict=safe` with `invariants_violated=0`. The final report covered all
Sprints 20–26.

---

## Gap Register

| ID | Step | Description | Severity | Status |
|----|------|-------------|----------|--------|
| — | — | No gaps identified | — | — |

---

## Observations (non-blocking)

### OBS-001 — Schedule tick requires min-interval to have elapsed

**Step:** 4 (scheduler tick)  
**Observation:** If the tick is called immediately after demo-seed, the scheduler
may skip the just-created schedule because `last_run_at` is within the
`min_interval_seconds` floor (60s). The tick returns `skipped_min_interval`,
not an error.  
**Impact:** None — this is correct behavior. The acceptance criterion is that the
tick executes without error and the audit trail reflects the skip reason.  
**Action:** Documented in runbook Step 4. No code change needed.

### OBS-002 — Evidence pack seed_result is optional

**Step:** 5 (assemble evidence pack)  
**Observation:** `seed_result` can be omitted (empty dict). The pack is still
assembled correctly. Passing the seed result from Step 3 enriches the notes in
the final report.  
**Impact:** None — both modes work correctly.  
**Action:** Documented in rehearsal script. No code change needed.

---

### OBS-003 — Full test suite must not run with a live server on the same SQLite DB

**Step:** N/A (test infrastructure)  
**Observation:** `test_skill_schedule_tick.py::test_tick_updates_next_run_at_after_dispatch`
fails intermittently when a uvicorn server using the same `erpguard.db` file is running
concurrently. SQLite serialises writes; under concurrent load the tick's
`update_skill_schedule` commit can be delayed past the test assertion window.  
**Impact:** None in CI (server not running). Non-blocking for TFM demo.  
**Workaround:** Stop the server before running `python -m pytest`.  
**Action:** Documented. No code change needed — the test logic is correct.

## Previous gaps (resolved in earlier sprints)

| Sprint | Gap | Resolution |
|--------|-----|------------|
| 22 | Replay without pre-check on empty Fake ERP | Added page state verifier with fail-closed gate |
| 23 | Version mutation after activation | Immutability enforced at lifecycle gate |
| 24 | Runner accepting non-active versions | `is_active` gate added |
| 25 | Concurrent schedule execution | Per-schedule TTL lock added |

---

## Next steps

None required for v0.13.0-rc1. The RC is ready for TFM defense.
