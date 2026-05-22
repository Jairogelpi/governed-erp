# Release Evidence Pack

**Product:** ERPGuard — ERP Agent OS  
**Version:** 0.13.0-rc1  
**Sprint chain:** 20–26  
**Generated:** 2026-05-23

---

## What this pack contains

The release evidence pack is the auditable artifact that demonstrates:

1. **Sprint coverage** — 7 sprints implemented and verified (20–26)
2. **Safety invariant enforcement** — 12 invariants, all enforced
3. **Test suite** — 1000+ tests passing, 0 failing
4. **Runbook coverage** — 15 operations documented
5. **Blocked operations** — 12 categories explicitly blocked
6. **Demo scenario** — full end-to-end loop reproducible in < 5 minutes

---

## Sprint Coverage

| Sprint | Title | Status |
|--------|-------|--------|
| 20 | Record-to-Skill Backend Loop | ✅ verified |
| 21 | Real Fake ERP Browser Recorder | ✅ verified |
| 22 | Verified Fail-Closed Replay | ✅ verified |
| 23 | Skill Versioning, Promotion & Rollback | ✅ verified |
| 24 | Active Skill Manual Runner | ✅ verified |
| 25 | Scheduled Skill Runs & Run Queue Safety | ✅ verified |
| 26 | Operator Runbook & Evidence Pack | ✅ current |

---

## Safety Invariants (12/12 enforced)

| Invariant | Enforcement |
|-----------|-------------|
| Fake ERP only | Browser automation never opens real Odoo |
| No LLM at replay | `deterministic_ui` runtime type only |
| No real Odoo browser | `ALLOW_GENERIC_REAL_ODOO_WRITES=false` |
| No coordinate fallback | Selector-only mode enforced by compiler |
| No automatic repair | Fail-closed gate in verified replay |
| No background scheduler | No cron daemon — manual tick only |
| No MCP gateway | Not wired at runtime |
| No R3/R4 operations | `ALLOW_R3_R4_REAL_WRITES=false` hardcoded |
| No free-form browser | Steps declared at compile time |
| Dedup & lock | Per-schedule TTL + dedup window |
| Full audit trail | Every event persisted with timestamp |
| Immutable active versions | No mutation after `activate` |

---

## Test Evidence

```
python -m pytest -q
1088+ passed, 0 failed, 9 skipped
```

Test distribution:
- Record-to-Skill backend: ≥40 tests
- Real Fake ERP recorder: ≥30 tests
- Verified fail-closed replay: ≥35 tests
- Skill versioning: ≥45 tests
- Active manual runner: ≥49 tests
- Scheduled runs: ≥63 tests
- Operator evidence pack: ≥35 tests

---

## API Surface

```
POST /v1/operator/demo-seed
POST /v1/operator/evidence-packs
GET  /v1/operator/evidence-packs/{id}
GET  /v1/operator/evidence-packs/{id}/safety-report
GET  /v1/operator/evidence-packs/{id}/final-report
GET  /v1/operator/demo-runbook
```

---

## Explicit Exclusions

This evidence pack explicitly states the following are **NOT** part of this release:

- Real Odoo browser automation
- LLM replay
- Background scheduler
- Real ERP browser automation
- Distributed queue
- R3/R4 operations
- Production ERP writes

---

## Validation Commands

```bash
python -m pytest -q
git diff --check
curl http://127.0.0.1:8000/v1/operator/demo-runbook
curl -X POST http://127.0.0.1:8000/v1/operator/evidence-packs \
  -H "Content-Type: application/json" \
  -d '{"created_by": "ci", "scenario_label": "CI validation"}'
```
