# Phase 17 — Governed Confirmation

## Outcome

ERPGuard now has one narrowly bounded R3 capability:
`sales.order.confirm`. It can invoke only `sale.order.action_confirm` for
one resolved order. It does not expose a generic Odoo model/method call,
invoice posting, picking validation, cancellation, deletion, or production
execution.

The capability is fail-closed by default:

```text
ERPGUARD_ALLOW_ODOO_GOVERNED_CONFIRMATION=false
```

The automated success path uses an injected in-memory staging transport.
A deliberately authorized live staging experiment was also performed. Odoo
confirmed the isolated test order, created a picking and unexpectedly
auto-posted an invoice. ERPGuard detected the forbidden invoice
postcondition and correctly marked the run `failed`; it did not claim a
successful governed confirmation.

## Governed sequence

```text
authenticated operator
→ approved immutable skill package
→ staging connection check
→ live order snapshot
→ R3 preflight and conservative effect prediction
→ ActionPlan/native-plan/snapshot hashes
→ independent exact-scope approval
→ signed single-use permit
→ state revalidation
→ connector-side state revalidation
→ bounded action_confirm
→ postcondition verification
→ sealed Evidence Pack
→ manual governed cleanup plan
```

## Preflight gates

Planning is blocked unless:

- the feature flag is explicitly enabled;
- connection metadata declares `environment=staging`;
- the order state is `draft` or `sent`;
- `amount_total` is at or below both the global ceiling and any lower
  connection ceiling;
- no configured forbidden marker appears in the order reference or product
  names;
- the order has no pre-existing invoices;
- the tenant kill switch is inactive;
- the approved skill package declares exactly the canonical capability.

The default global amount ceiling is `1000`. It can be lowered through
`ERPGUARD_ODOO_CONFIRMATION_AMOUNT_CEILING` or connection metadata. Connection
metadata cannot raise it above the global value.

## Snapshot and drift protection

The approval snapshot includes order identity/state, partner, company,
currency, total, client reference, write date, normalized lines, picking
states and invoice states. Its deterministic hash is:

- persisted on the run;
- included in the exact approval scope;
- signed as part of the permit;
- injected into the stored native plan.

ERPGuard re-reads the snapshot before approval and immediately before
execution. The Odoo connector re-reads it once more before
`action_confirm`. Any mismatch consumes no ERP write and returns
`state_changed_before_approval`, `state_changed_since_approval`, or
`state_snapshot_mismatch`.

## Approval contract

For `sales.order.confirm`, an approval:

- cannot be omitted;
- must be created by a different actor from the planner;
- must be bound by exact scope
  `run:{run_id}:sales.order.confirm:{state_snapshot_hash}:{control_contract_hash}`;
- can only be bound by its own approver;
- can only be executed by the actor who planned the run;
- is single-use;
- is included in the permit signature;
- expires with the permit, with a maximum TTL of 900 seconds.

## Outcomes and evidence

Terminal states now describe reality:

- `succeeded`: postconditions verified;
- `blocked`: no write because a connector or governance gate blocked;
- `failed`: a known execution/postcondition failure;
- `unknown`: transport outcome could not be established.

After a terminal outcome:

```text
GET /v1/runs/{run_id}/evidence
GET /v1/runs/{run_id}/cleanup-plan
```

The Evidence Pack contains the action plan, native plan, approved snapshot,
hashes, permit metadata, approval provenance, connector outcome,
postconditions, generated picking IDs, timestamps and cleanup strategy. It
is sealed with a deterministic digest and checked when read.

## Postconditions

A successful confirmation requires:

- the same order identity;
- resulting state `sale` or `done`;
- no invoice IDs created by confirmation;
- captured generated picking IDs;
- a verified connector result.

A timeout after the RPC is not retried blindly. ERPGuard attempts a
read-back; verified confirmed state can recover the result, otherwise the
run remains `unknown`.

## Cleanup boundary

Phase 17 does not claim universal rollback. Confirmation can create stock,
procurement, purchase or manufacturing effects. The stored cleanup plan is
manual and requires a fresh read, downstream-state inspection and a future
separately approved allowlisted cancellation capability. ERPGuard never
automatically calls `action_cancel` or deletes evidence.

For the authorized staging experiment, the operator separately authorized
manual compensation after inspecting the generated effects. The uncompleted
picking was cancelled, a linked credit note was created and posted for the
unexpected posted invoice, and the order was cancelled. Final read-back
proved zero residual on both accounting documents, net document total zero,
no completed delivery and a cancelled order. This is compensation, not
rollback: the original posted invoice and its reversing credit note remain
as accounting evidence.

## Verification

Focused automated coverage:

```text
python -m pytest \
  tests/test_phase14_skill_compiler.py \
  tests/test_phase15_execution_permit_runtime.py \
  tests/test_phase16_odoo_quote_draft.py \
  tests/test_phase17_governed_confirmation.py -q
```

The tests cover safe injected-staging confirmation, exact independent
approval, empty/wrong/self approval blocks, state drift, production block,
amount ceiling, disabled feature flag, postconditions, Evidence Pack and
manual cleanup plan.

The sanitized live evidence is stored in
`docs/demo/phase17_governed_confirmation_live_staging_evidence.json`.
Credentials and commercial master data are not included.

The experiment proves the controlled-failure path against real Odoo 19
staging. It also proves that this staging database has an automation that
can post an invoice during confirmation, so real confirmation must remain
disabled by default until the postcondition policy and operational controls
are explicitly redesigned and reviewed.

Phase 17.1 completes that hardening without adding another write capability.
See `docs/specs/86_phase17_1_confirmation_side_effect_contract.md`.
