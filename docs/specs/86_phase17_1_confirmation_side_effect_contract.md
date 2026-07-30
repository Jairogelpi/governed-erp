# Phase 17.1 — Confirmation Side-Effect Contract

## Outcome

Phase 17.1 converts the live staging lesson into an immutable execution
contract. It adds no new ERP write, cancellation or accounting capability.
`sales.order.confirm` remains staging-only and disabled by default.

Every governed confirmation now binds the exact live order snapshot, a
read-only automation fingerprint, and a versioned side-effect budget plus
compensation plan. Their hashes are persisted, included in the native plan,
covered by the permit signature and represented in the exact approval scope.
A fingerprint change before approval or execution blocks the write.

## Default side-effect budget

```json
{
  "required_effects": ["sale_order_confirmation"],
  "allowed_effects": ["stock_picking_creation", "stock_reservation"],
  "forbidden_effects": [
    "stock_picking_completion",
    "invoice_creation",
    "invoice_posting",
    "payment_creation",
    "purchase_order_creation",
    "manufacturing_order_creation"
  ],
  "maximum_created_records": {
    "stock.picking": 1,
    "account.move": 0,
    "account.payment": 0,
    "purchase.order": 0,
    "mrp.production": 0
  },
  "conditional_effects": {
    "stock_picking_creation": "within ceiling and never done",
    "stock_reservation": "generated uncompleted picking only"
  }
}
```

The budget is deliberately conservative. This phase has no metadata switch
that silently weakens these defaults.

## Automation fingerprint

The bounded read-only inspection records Odoo version, relevant installed
modules, readable active automated-action count for `sale.order`, custom
sale-order fields, model permissions, line invoicing-policy signals and
downstream-model observability. Evidence is normalized and hashed; automated
action names and commercial records are not stored.

If the required modules, fields, automation rules, permissions or downstream
models cannot be inspected, the fingerprint is incomplete and planning
blocks. This is a capability fingerprint, not proof that every custom Odoo
module has been semantically understood.

## Effect evaluation

Before/after snapshots compare record identities for `stock.picking`,
`account.move`, `account.payment`, `purchase.order` and `mrp.production`.
The evaluator also detects the order transition and invoices that became
posted. A missing required effect, observed forbidden effect or exceeded
record ceiling produces `budget_exceeded`; the run is `failed` even if Odoo
technically completed `action_confirm`.

## CompensationPlan

The stored plan is structured and versioned: trigger, separate required
approval, affected records, compensating capabilities, expected neutral
effect, verification, residual effects and operator instructions.

It never authorizes compensation by itself. Compensating capability names
are descriptive future allowlist names, not executable capabilities added by
this phase. A posted invoice must be neutralized with a linked credit note
and zero-residual verification; deletion is never acceptable.

## Permanent regression

```text
action_confirm
→ sale order becomes sale
→ picking created
→ posted invoice created
→ side-effect budget exceeded
→ run failed
→ Evidence Pack preserves observations
→ CompensationPlan identifies affected invoice
```

The regression does not contact Odoo and does not execute compensation.

## Exit criteria

- side-effect budget is versioned and immutable;
- incomplete fingerprint blocks;
- snapshot and control-contract drift block before the write;
- observed record counts are compared with explicit ceilings;
- unexpected invoice creation/posting rejects success;
- typed CompensationPlan is materialized with affected IDs;
- Evidence Packs include contract, hashes and evaluation;
- the real feature flag remains false by default.
