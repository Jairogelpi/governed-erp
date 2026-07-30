# 09 Security Model Spec

**Parent spec references:** Sections 5, 8.3, 11, 13, 14, 18, 21, 26, 30.

## Purpose

Define the Phase 1 security model for a preflight-only backend.

## Security Principles

- Fail closed on uncertain state.
- Never expose connection secrets in API responses.
- Treat all actor data as untrusted input.
- Do not allow Phase 1 endpoints to execute ERP write actions.
- Store enough audit evidence to reconstruct decisions.
- Keep LLMs outside the execution boundary.

## Actor Model

Phase 1 accepts actor metadata in the preflight request:

```json
{
  "type": "user",
  "native_user_id": "6",
  "display_name": "Jairo"
}
```

This is recorded for audit but is not yet a complete authorization system. Parent spec permission rules remain a later expansion.

## Connection Secrets

Connection config may contain sensitive values. Phase 1 must:

- avoid returning raw config from list/get endpoints;
- isolate serialization models for public responses;
- prepare for later encryption or secret-manager integration.

## Risk Model

`confirm_sales_order` is R3 by default. Because Phase 1 does not execute actions, R3 means the preflight response can be `allow`, `require_approval`, or `block`, but no write is performed.

The later bounded `sales.order.confirm` capability remains R3 and adds
effect risk. A successful RPC is not a successful governed run unless
observed effects remain inside the signed side-effect budget. Invoice or
payment creation/posting, undeclared purchase/manufacturing creation,
fingerprint uncertainty and contract drift are hard failures or pre-write
blocks. Compensation never changes the original failure classification.

## Audit Requirements

For every preflight request, record:

- actor;
- action;
- canonical object/action;
- state snapshot;
- policies applied;
- invariant results;
- decision;
- timestamp.

## Out of Scope

- Full authentication/authorization.
- Approval flows.
- Secret encryption at rest.
- Odoo record-rule simulation.
- Payment or financial execution.
