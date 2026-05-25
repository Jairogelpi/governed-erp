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

### OBS-003 — SQLite write lock contention between tests (QueuePool stale connections)

**Step:** N/A (test infrastructure)  
**Observation:** Several scheduler and replay tests failed intermittently with
`sqlite3.OperationalError: database is locked` during `session.commit()`.
The original note blamed a concurrent uvicorn server, but the actual root cause
is the SQLAlchemy `QueuePool` (default for file-based SQLite engines): after
`session.close()`, the pool returns the connection to its internal cache without
physically closing the underlying `sqlite3` connection. The next test opens a new
`SessionLocal()` which gets a fresh physical connection from the OS; that
connection tries to acquire an exclusive write lock but SQLite refuses because the
pooled connection from the previous test still holds a shared/deferred lock on the
same file.

Affected tests:
- `test_skill_schedule_tick.py::test_tick_dispatches_due_active_schedule`
- `test_skill_schedule_tick.py::test_tick_dedups_within_window`
- `test_skill_schedule_tick.py::test_tick_updates_next_run_at_after_dispatch`
- `test_skill_schedule_tick.py::test_tick_creates_queue_entries`
- `test_rc_validation_contract.py::test_scheduler_tick_returns_200`
- `test_ui_replay_audit_service.py::test_audit_entries_match_step_count`

**Root cause:** `QueuePool` with file SQLite keeps physical connections open between
tests, causing OS-level write-lock conflicts between consecutive test sessions.

**Fix (Sprint 33):** `erpguard/db/session.py` now uses `NullPool` for file SQLite
so `session.close()` physically closes the underlying `sqlite3` connection and
releases all OS-level locks immediately. `PRAGMA journal_mode=WAL` and
`PRAGMA busy_timeout=30000` are also set on each new connection for additional
concurrency robustness.

**Status:** Fixed in commit for Sprint 33.

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
