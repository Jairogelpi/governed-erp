# TFM Defense Script

**Product:** ERPGuard — ERP Agent OS  
**Context:** Trabajo de Fin de Máster — defense presentation  
**Duration:** ~20 minutes demo + Q&A

---

## Opening (2 min)

> "This project builds a semantic safety layer for ERP operations. The core idea is that an operator can **record a process on a fake ERP, compile it into a deterministic skill, verify it, version it, and schedule it** — without any LLM involvement at execution time, and without any autonomous background scheduler."

> "Everything I show you today runs locally. The ERP target is a Fake ERP server running on localhost. There is no real Odoo, no real browser automation of a production system, and no free-form AI agent."

---

## Live Demo (10 min)

### Step 1 — Open the demo dashboard

```
http://127.0.0.1:8000/demo
```

> "This is the operator dashboard. Each section corresponds to a sprint. I'll walk through the Record-to-Skill flow, which starts at Sprint 21."

### Step 2 — Seed the full demo

In the **Operator Evidence Pack** section:

1. Click **Seed Full Demo** → shows all created IDs
2. Click **Assemble Evidence Pack** → shows pack with safety checks
3. Click **Safety Report** → shows 12/12 invariants enforced
4. Click **Final Report** → shows the complete demo report

> "The demo seed automatically runs the full loop: record → compile → verify → version → activate → run → schedule. The evidence pack captures all the artifacts."

### Step 3 — Show the scheduler

In the **Scheduled Skill Runs** section:

1. Use the version ID from the seed
2. Click **Get Schedule** → shows the 60s schedule
3. Click **Tick scheduler** → shows tick report (dispatched/skipped/failed)
4. Click **Events** → shows full audit trail

> "The tick is completely manual. There is no cron daemon, no background worker. Every dispatch goes through the same verified replay stack as a manual run."

### Step 4 — Show the runbook

```
GET /v1/operator/demo-runbook
```

> "The runbook documents 15 operations across 7 sprints. Every operation has a safety note explaining what it does and does not allow."

---

## Q&A Preparation

### "Why Fake ERP and not real Odoo?"

> "The Fake ERP gives us a controlled, deterministic target that can be replayed without side effects. Adding real Odoo connectivity is Sprint 27+ — it requires additional safety controls that are out of scope for this TFM."

### "Why no LLM at replay time?"

> "Deterministic replay means every run is auditable and comparable. LLM involvement would make each run non-deterministic. The goal is a safety layer, not a general-purpose agent."

### "Why manual tick only?"

> "A production-grade autonomous scheduler requires distributed locking, dead-letter queues, and concurrency controls. The manual tick demonstrates the scheduling logic — lock, dedup, dispatch, audit — without the operational complexity. The design is production-ready but the trigger is deliberately manual for this TFM."

### "What prevents a bad actor from calling the tick in a loop?"

> "Three controls: (1) the minimum interval floor enforced per schedule (60s default), (2) the per-schedule execution lock with TTL that prevents concurrent runs, and (3) the dedup window that skips identical inputs within a time window."

### "Is this production-ready?"

> "The safety architecture is production-ready. The operational hardening — real scheduler, monitoring, alerting, multi-tenant isolation — is documented as the next phase. This TFM delivers the safety layer and its evidence."

---

## Closing (1 min)

> "The full loop — record, compile, verify, version, activate, run, schedule — is implemented in 7 sprints, covered by 1000+ tests, and packaged in a reproducible evidence pack. Every safety invariant is enforced and documented. The system is ready for the next phase: real ERP connectivity with the same safety layer in place."
