# Operator Demo Overview

**Product:** ERPGuard — ERP Agent OS  
**Version:** 0.13.0-rc1  
**Sprint chain:** 20–26  
**Date:** 2026-05-23

## What this demo shows

ERPGuard is a semantic safety layer that lets an operator **record a browser process on a Fake ERP, compile it into a deterministic skill, verify it with fail-closed replay, version and approve it, run it manually, and schedule it** — all without LLM involvement at execution time, without real Odoo browser automation, and without any autonomous background scheduler.

## The full loop (Sprints 20–26)

```
Record browser process on Fake ERP          ← Sprint 21
  → Generate UI skill draft                 ← Sprint 20
  → Compile deterministic UI skill          ← Sprint 20
  → Verified fail-closed replay             ← Sprint 22
  → Immutable versioning / promotion        ← Sprint 23
  → Approval / activation                   ← Sprint 23
  → Active manual runner                    ← Sprint 24
  → Scheduled manual-tick runner            ← Sprint 25
    (dedup / lock / audit)
  → Evidence pack                           ← Sprint 26
  → Safety report                           ← Sprint 26
  → Final demo report                       ← Sprint 26
```

## What is NOT in scope

| Excluded                              | Why                                      |
|---------------------------------------|------------------------------------------|
| Real Odoo browser automation          | Hard constraint — Fake ERP only          |
| LLM at replay time                    | Deterministic replay enforced            |
| Autonomous background scheduler       | Manual tick only                         |
| Distributed queue (Celery, RQ)        | Not needed — single-process              |
| MCP execution gateway                 | Not wired at runtime                     |
| R3/R4 ERP write operations            | `ALLOW_R3_R4_REAL_WRITES=false` hardcoded |
| Coordinate-based click fallback       | Selector-based only                      |
| Automatic repair on replay failure    | Fail-closed — no auto-fix                |

## Demo surface

Open `GET /demo` in a browser. Each sprint has its own section. Sprint 26 adds the **Operator Evidence Pack** section at the top.

## Quick validation

```bash
python -m pytest -q          # 1000+ passed, 0 failed
git diff --check             # 0 whitespace errors
GET /v1/operator/demo-runbook
POST /v1/operator/evidence-packs
```
