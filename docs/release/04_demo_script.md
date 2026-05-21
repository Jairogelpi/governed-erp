# Demo Script — ERPGuard v0.12.0-rc1

## Setup (2 min)

```bash
pip install -e ".[dev]"
uvicorn apps.api.main:app --reload --port 8000
```

Navigate to `http://localhost:8000/demo`.

## Act 1: Release health (1 min)

1. Click **Release health** → status=ok, safety_boundaries_locked=true
2. Click **Readiness report** → readiness_score=100, 8/8 checks passed
3. Click **Safety boundaries** → show all locks, R1/R2 whitelists, blocked ops

**Key message**: Everything is locked by default. No writes can happen without explicit opt-in.

## Act 2: Operator flow (3 min)

1. Click **Seed demo data** → tenant + skill + session created
2. Click **Create operator session**
3. Click **Run full safe read-only path** → auto-advances through all safe steps
4. Click **View timeline** → show every step with status
5. Click **View summary** → progress %, known IDs, `can_execute_real_writes=false`

**Key message**: The operator never copies IDs manually. The session tracks state.

## Act 3: Write governance (2 min)

1. Scroll to **R2 Controlled Write Pilot**
2. Enter a skill ID → click **Create R2 request**
3. Click **Check R2 policy** → show BLOCKED (feature flag off)
4. Show violations: feature_flag_disabled, missing_write_readiness_certification
5. Scroll to **R2 Pilot Evidence Review** → enter run ID → **Evidence review**, **Rollback rehearsal**, **Promotion gate**
6. Show: promotion gate BLOCKED until all 9 checks pass

**Key message**: Even when enabled, every write requires certification, double approval, snapshots, and a reviewable promotion gate.

## Act 4: Smoke test (1 min)

1. Click **Run operator smoke test** → 7 checks, all pass
2. Show: `smoke_status: passed`

## Close

> "This is the governance layer. The ERP runs underneath. ERPGuard ensures no unreviewed write ever reaches Odoo."
