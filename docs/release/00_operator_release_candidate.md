# ERPGuard v0.12.0-rc1 — Operator Release Candidate

## What this is

ERPGuard is an ERP Agent OS that governs Odoo ERP access with safety controls at every layer. This release candidate packages the first 12 sprints into a reproducible, operator-facing product.

## Sprint chain

| Sprint | Capability |
|--------|-----------|
| 1 | Odoo read-only connection |
| 2 | Business analysis + opportunities + ROI |
| 3 | Safe skill compilation + dry-run proof |
| 4 | Approval workflow + activation gates |
| 5 | Limited execution sandbox |
| 6 | Real read execution + live evidence |
| 7 | Write readiness risk certification |
| 8 | First controlled R1 write pilot (mail.message) |
| 9 | Production safety + tenant controls |
| 10A | End-to-end operator flow UI |
| 10B | First R2 controlled write pilot (res.partner, staging) |
| 11 | R2 evidence review + rollback rehearsal + readiness gate |
| 12 | Operator release candidate packaging |

## Safety boundaries (permanent)

- `ALLOW_REAL_ODOO_WRITES=false`
- `ALLOW_GENERIC_REAL_ODOO_WRITES=false`
- `ALLOW_R3_R4_REAL_WRITES=false`
- `ALLOW_R1_REAL_WRITE_PILOT=false` (default)
- `ALLOW_R2_REAL_WRITE_PILOT=false` (default)
- `can_execute_real_writes=false` in every response
- `approved_for_real_execution=false` always

## Blocked operations (hard-coded)

- `sale.order.action_confirm` (real)
- `stock.picking.button_validate` (real)
- `account.move.action_post` (real)
- `mrp.production.button_mark_done` (real)
- Any generic `create/write/unlink/copy/action_*/button_*`

## Quick start

See `01_install_and_run.md`.
