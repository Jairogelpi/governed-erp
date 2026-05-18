# 22 Human Recording v0.2.1 Hardening

**Status:** Implementation spec for controlled human recording hardening
**Date:** May 18, 2026
**Relationship to v0.2:** Tightens the existing controlled Fake ERP recording path without expanding product scope.

## Purpose

Human Recording v0.2 proved that a user can manually perform the Fake ERP formula review flow, capture structured events, compile the recording into a deterministic skill, and run allow/block checks.

v0.2.1 hardens that path by making the compiler explicit about the minimum supported event sequence and by showing a small recording preview/readiness panel in `/demo` before compilation.

The goal is better diagnosability and demo confidence, not broader automation.

## Exact Scope

This block changes only:

- the Fake ERP recording-to-skill compiler validation;
- the existing `/demo` HTML and vanilla JavaScript human recording area;
- focused tests for valid and incomplete controlled recordings;
- README and AGENTS notes.

The supported flow remains:

```text
Fake ERP sales orders
-> search order
-> open order
-> formula tab
-> review formula
-> compile deterministic skill
-> run Formula Guard allow/block
```

## Non-Goals

This block must not add:

- LLM interpretation;
- MCP;
- browser extension recording;
- unrestricted recording of arbitrary websites;
- real Odoo UI automation;
- real ERP write actions;
- new ERP adapters;
- frontend frameworks such as React, Vite, or Tailwind;
- broad UI redesign;
- changes to `POST /v1/demo/full-record-to-skill-flow`.

## Expected Event Contract

The compiler supports a finished Fake ERP recording only when the ordered events contain the minimum sequence below:

1. `navigate` event opening `/fake-erp/sales/orders`;
2. `fill` event on selector `[data-testid='order-search']` with a supported order reference;
3. `click` event on selector `[data-testid='open-order-<order_reference>']`;
4. `click` event on selector `[data-testid='formula-tab']`;
5. `click` event on selector `[data-testid='review-formula']`.

The compiler may tolerate extra events before, between, or after these events, but the required events must appear in order.

Supported order references remain the existing Fake ERP references:

- `SO-VALID`
- `SO-FORMULA-MISMATCH`
- `SO-CAPACITY-NO-FORMULA`
- `SO-EMPTY-LINES`

## Compiler Diagnostic Errors

When the sequence is incomplete or unsupported, the compiler must raise `ValueError` with one of these exact messages:

- `missing_sales_orders_navigation`
- `missing_order_search_event`
- `missing_open_order_event`
- `missing_formula_tab_event`
- `missing_review_formula_event`
- `unsupported_order_reference`
- `unsupported_fake_erp_formula_flow`

The compile API can continue wrapping these in its existing `unsupported_recording_flow` error code, but the message must preserve the compiler diagnostic string.

## Minimal `/demo` UI Changes

After a user finishes a human recording, `/demo` should show a preview containing:

- `recording_id`;
- `status`;
- `event_count`;
- ordered event summaries;
- captured selectors;
- compiler readiness as `ready` or `not_ready`.

The preview is advisory only. It does not add a new backend endpoint and does not replace server-side compiler validation.

## Expected Tests

Add or update tests to prove:

- a valid human recording still compiles and runs `SO-VALID -> allow` and `SO-FORMULA-MISMATCH -> block`;
- a recording without the search event fails with `missing_order_search_event`;
- a recording without the formula tab event fails with `missing_formula_tab_event`;
- a recording without the review formula event fails with `missing_review_formula_event`;
- `/demo` includes the preview/readiness zone;
- `GET /health` still returns `{"status": "ok"}`.

## Acceptance Criteria

This block is accepted when:

- the new compiler diagnostics are deterministic and covered by tests;
- the existing valid human recording path remains compatible;
- `/demo` shows event preview/readiness after finish recording using only HTML and vanilla JavaScript;
- the full test suite passes or any browser skips are reported precisely;
- README and AGENTS are updated;
- no LLM, MCP, browser extension, real Odoo UI, unrestricted recorder, real ERP write action, or broad UI rewrite is introduced.
