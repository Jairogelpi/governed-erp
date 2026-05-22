# Safety Boundaries

**Product:** ERPGuard — ERP Agent OS  
**Sprint chain:** 20–26

---

## Enforced Safety Invariants

| # | Invariant | Status | Detail |
|---|-----------|--------|--------|
| 1 | Fake ERP only | **enforced** | All browser automation targets local Fake ERP only |
| 2 | No LLM at replay time | **enforced** | Skill replay is fully deterministic |
| 3 | No real Odoo browser automation | **enforced** | `ALLOW_GENERIC_REAL_ODOO_WRITES=false` |
| 4 | No coordinate-based fallback | **enforced** | All selectors are deterministic CSS/testid-based |
| 5 | No automatic repair on failure | **enforced** | Replay is fail-closed — no auto-fix attempted |
| 6 | No background/autonomous scheduler | **enforced** | Manual tick only — no cron daemon |
| 7 | No MCP execution gateway | **enforced** | No MCP tool calls at skill runtime |
| 8 | No R3/R4 operations | **enforced** | `ALLOW_R3_R4_REAL_WRITES=false` always |
| 9 | No free-form browser agent | **enforced** | Steps declared at compile time only |
| 10 | Dedup & execution lock | **enforced** | Per-schedule TTL lock + dedup window |
| 11 | Full audit trail | **enforced** | Every run, step, tick persisted with timestamp |
| 12 | Immutable active versions | **enforced** | Active versions cannot be mutated |

---

## Blocked Operations

The following operations are **never** permitted in this system:

- Real Odoo browser automation (`sale.order.action_confirm`, `account.move.action_post`, etc.)
- Free-form browser agent with LLM-driven navigation
- Coordinate-based click fallback
- Automatic repair on replay failure
- Background / autonomous cron scheduler
- Distributed job queue (Celery, RQ, etc.)
- MCP execution gateway at skill runtime
- R3/R4 ERP write operations
- New ERP write categories beyond existing approved pilots
- LLM calls at replay time
- Multi-node scheduler
- Production ERP writes of any kind

---

## Safety Configuration

```env
ALLOW_GENERIC_REAL_ODOO_WRITES=false   # must stay false
ALLOW_R3_R4_REAL_WRITES=false          # hardcoded off — not overridable
ALLOW_R2_REAL_WRITE_PILOT=false        # off by default
ALLOW_R1_REAL_WRITE_PILOT=false        # off by default
```

---

## Defense Notes for TFM Review

1. **Why Fake ERP only?** The goal of Sprints 20–26 is to demonstrate the safety layer in isolation, before any real ERP connectivity is added. The Fake ERP provides a controlled, deterministic target that can be replayed without side effects.

2. **Why no LLM at replay time?** Deterministic replay means the skill can be audited, replayed, and compared step-by-step. LLM involvement would make each run non-deterministic and unauditable.

3. **Why manual tick only?** A production-grade autonomous scheduler requires concurrency controls, distributed locking, and dead-letter queues that are out of scope for this TFM. The manual tick demonstrates the scheduling logic without the operational complexity.

4. **Why fail-closed?** A fail-closed replay means a verification failure stops the step rather than attempting recovery. This is the safer default for any ERP automation system.
