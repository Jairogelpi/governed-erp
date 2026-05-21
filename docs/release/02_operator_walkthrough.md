# Operator Walkthrough

## 1. Check release health

`GET /v1/release/health` — confirms DB, version, and safety locks.

## 2. Seed demo data

`POST /v1/release/demo-seed` — creates a demo tenant, skill, and operator session.

## 3. Open the operator flow

In `/demo`, scroll to **ERP Agent OS — End-to-End Operator Flow**:

1. Click **Create operator session**
2. Optionally enter a connection ID and click **Select connection**
3. Click **Run next step** to advance through each flow step
4. Or click **Run full safe read-only path** to run all safe steps automatically

## 4. Review the timeline

Click **View timeline** to see every executed step with status and detail.

## 5. Check summary and safety invariants

Click **View summary** to confirm:
- Progress %
- Known IDs accumulated
- `can_execute_real_writes=false`
- `allow_generic_real_odoo_writes=false`

## 6. Run the smoke test

`POST /v1/release/operator-smoke` — runs 7 automated checks end-to-end.

## 7. View safety boundaries

`GET /v1/release/safety-boundaries` — lists all write locks, allowed models, allowed fields, and notes.
