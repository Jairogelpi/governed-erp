# Safety Boundaries

## Feature flags (all false by default)

| Flag | Default | Effect |
|------|---------|--------|
| `ALLOW_REAL_ODOO_WRITES` | `false` | Master write lock |
| `ALLOW_GENERIC_REAL_ODOO_WRITES` | `false` | Blocks all non-whitelisted writes |
| `ALLOW_R3_R4_REAL_WRITES` | `false` | Blocks R3/R4 risk tier writes |
| `ALLOW_R1_REAL_WRITE_PILOT` | `false` | Blocks mail.message.create |
| `ALLOW_R2_REAL_WRITE_PILOT` | `false` | Blocks res.partner.write |
| `ERPGUARD_ALLOW_ODOO_GOVERNED_CONFIRMATION` | `false` | Independently blocks bounded staging confirmation |

## R1 write pilot (Sprint 8)

- Model: `mail.message`
- Method: `create` only
- Requires: write readiness certification + double approval + idempotency key
- Blocked by default. Enable with `ALLOW_R1_REAL_WRITE_PILOT=true` in environment.

## R2 write pilot (Sprint 10B)

- Model: `res.partner`
- Fields: `comment`, `website` only
- Environments: `staging`, `demo` only
- Requires: write readiness certification + 2 distinct approvers + idempotency key + pre/post snapshots
- Blocked by default. Enable with `ALLOW_R2_REAL_WRITE_PILOT=true` in environment.

## Governed R3 exception

`sale.order.action_confirm` exists only behind the canonical
`sales.order.confirm` capability. It requires staging metadata, amount and
marker gates, complete automation fingerprint, immutable effect budget,
independent exact-scope approval, signed one-use permit and postconditions.
It remains disabled by default and is not authorized for production.

## Permanently blocked outside explicit bounded capabilities

- `stock.picking.button_validate`
- `account.move.action_post`
- `mrp.production.button_mark_done`
- Any `action_*` or `button_*` beyond the R1/R2 whitelist
- Any `create/write/unlink/copy` on non-whitelisted models

## R2 promotion gate (Sprint 11)

Before any R2 run can be "promoted", 9 checks must pass:

1. Run has terminal status
2. Evidence review completed
3. No field drift detected
4. Rollback rehearsal completed
5. Rollback rehearsal passed
6. Execution report generated
7. Residual risk score ≤ 30
8. Generic writes locked (permanent)
9. R3/R4 writes locked (permanent)
