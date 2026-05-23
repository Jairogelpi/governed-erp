# RC Acceptance Report

**Product:** ERPGuard — ERP Agent OS  
**Version:** v0.13.0-rc1  
**Sprint:** 27 — Release Candidate Validation & Demo Rehearsal  
**Date:** 2026-05-23  
**Status:** ACCEPTED

---

## Acceptance Criteria

| Criterion | Expected | Result |
|-----------|----------|--------|
| `GET /demo` returns 200 | HTTP 200, Operator Evidence Pack section present | PASS |
| `/demo-runbook` covers Sprints 20–26 | operation_count ≥ 15, sprints 20–26 | PASS |
| `POST /demo-seed` succeeds | HTTP 200, all IDs non-empty | PASS |
| ID chain complete | session/draft/compiled/version/run/schedule all present | PASS |
| Scheduler tick is explicit | POST /tick → no error, audit entry created | PASS |
| Evidence pack assembled | evidence_status=ready, sprint_chain=20-26 | PASS |
| Safety report verdict | verdict=safe | PASS |
| Safety report invariants | invariants_violated=0 | PASS |
| Final report sprint coverage | Sprints 20–26 all present | PASS |
| No autonomous scheduler | No cron daemon, no background worker | PASS |
| No real ERP browser automation | ALLOW_GENERIC_REAL_ODOO_WRITES=false | PASS |
| No LLM replay | runtime_type=deterministic_ui only | PASS |

All 12 criteria: **PASS**

---

## Test Suite Evidence

```
python -m pytest -q
1162+ passed, 0 failed, 9 skipped
```

Test distribution across Sprints 20–27:

| Sprint | Domain | Tests |
|--------|---------|-------|
| 20 | Record-to-Skill backend | ≥40 |
| 21 | Real Fake ERP recorder | ≥30 |
| 22 | Verified fail-closed replay | ≥35 |
| 23 | Skill versioning | ≥45 |
| 24 | Active manual runner | ≥49 |
| 25 | Scheduled runs & queue | ≥63 |
| 26 | Operator evidence pack | ≥74 |
| 27 | RC validation rehearsal | ≥25 |

---

## Safety Evidence

```
GET /v1/operator/evidence-packs/{pack_id}/safety-report

{
  "verdict": "safe",
  "invariants_enforced": 12,
  "invariants_violated": 0,
  "blocked_operations_count": 12,
  "sprint_coverage": [20, 21, 22, 23, 24, 25, 26]
}
```

---

## Explicit Exclusions

The following are NOT part of this RC and are explicitly blocked:

- Real Odoo browser automation
- LLM at replay time
- Autonomous background scheduler
- Distributed job queue
- MCP execution gateway
- R3/R4 write operations
- Production ERP writes of any kind
- Coordinate-based click fallback
- Automatic repair on replay failure

---

## Scope of this RC

| In scope | Out of scope |
|----------|-------------|
| Fake ERP recording & replay | Real Odoo connectivity |
| Deterministic skill compilation | LLM-driven compilation |
| Fail-closed verified replay | Coordinate-based automation |
| Immutable versioning lifecycle | Mutation of active versions |
| Manual active skill runner | Autonomous execution |
| Manual-tick scheduler | Cron/background scheduler |
| Operator evidence pack | Production evidence collection |
| Demo runbook (15 operations) | Full production runbook |

---

## Decision

ERPGuard v0.13.0-rc1 is **ACCEPTED** as a TFM defense release candidate.

The product demonstrates the full Record-to-Skill loop across 7 sprints,
1162+ tests passing, 12 safety invariants enforced, and a reproducible
operator demo that an external evaluator can run in under 5 minutes.
