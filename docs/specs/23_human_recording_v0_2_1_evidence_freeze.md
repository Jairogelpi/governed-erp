# 23 Human Recording v0.2.1 Evidence Freeze

**Status:** Evidence and documentation freeze
**Date:** May 18, 2026
**Baseline commit:** `9e2642e feat: harden human recording v0.2.1`
**Evidence artifact:** `docs/demo/human_recording_v0_2_1_success_response.json`

## Purpose

This document freezes the evidence state after Human Recording v0.2.1 hardening.

The block is documentation and evidence only. It does not expand runtime scope, architecture, ERP coverage, or UI design.

## Exact v0.2.1 State

Human Recording v0.2.1 supports one controlled Fake ERP recording path:

```text
Fake ERP sales orders
-> search order
-> open order
-> formula tab
-> review formula
-> compile deterministic skill
-> run Formula Guard allow/block
```

The implementation includes:

- controlled capture on Fake ERP pages when `recording_id` is present;
- `RecordingSession` and ordered `RecordingEvent` persistence;
- compiler validation for the minimum supported sequence;
- clear compiler diagnostics for incomplete recordings;
- `/demo` preview/readiness for the recorded event list;
- deterministic skill replay with `llm_required_for_repeated_runs=false`;
- Formula Guard allow/block proof for `SO-VALID` and `SO-FORMULA-MISMATCH`.

## What The System Proves Now

The system now proves that:

- a human-style controlled recording can be represented as ordered structured events;
- the compiler can reject incomplete recordings before creating a skill;
- a complete recording compiles into a deterministic reusable skill;
- repeated skill runs do not require an LLM;
- ERPGuard allows a valid order and blocks an invalid formula order;
- evidence can be inspected as a JSON artifact for TFM evaluation.

## Minimum Required Event Sequence

The compiler accepts a recording only when the ordered events contain:

1. `navigate` to `/fake-erp/sales/orders`;
2. `fill` on `[data-testid='order-search']` with a supported order reference;
3. `click` on `[data-testid='open-order-<order_reference>']`;
4. `click` on `[data-testid='formula-tab']`;
5. `click` on `[data-testid='review-formula']`.

Extra events may exist, but these required events must appear in order.

## Supported Negative Diagnostics

Incomplete or unsupported recordings fail closed with one of these compiler messages:

- `missing_sales_orders_navigation`
- `missing_order_search_event`
- `missing_open_order_event`
- `missing_formula_tab_event`
- `missing_review_formula_event`
- `unsupported_order_reference`
- `unsupported_fake_erp_formula_flow`

The API continues to wrap compiler failures with `unsupported_recording_flow`, while preserving the diagnostic string in the error message.

## Evidence Artifact

The frozen evidence response is:

```text
docs/demo/human_recording_v0_2_1_success_response.json
```

It was generated from a real FastAPI `TestClient` flow that:

- created a recording session;
- posted the five required controlled events;
- finished the recording;
- compiled the recording into a skill;
- ran the skill for `SO-VALID`;
- ran the skill for `SO-FORMULA-MISMATCH`.

The evidence records:

- `recording_status = finished`;
- `event_count = 5`;
- `compiler_readiness = ready`;
- `valid_decision = allow`;
- `invalid_decision = block`;
- `invalid_issues_count = 1`;
- `repeated_execution_token_cost = 0`;
- all v0.2.1 proof flags set to `true`.

## Using `/demo`

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

Use the Human Recording controls:

1. start human recording;
2. open Fake ERP sales orders;
3. search `SO-FORMULA-MISMATCH`;
4. open the order;
5. open the formula tab;
6. click review formula;
7. finish recording;
8. inspect the preview/readiness panel;
9. compile recording;
10. run compiled skill.

## Compiler Readiness Meaning

`compiler_readiness = ready` means the preview contains the minimum selector/event evidence needed by the compiler:

- sales orders navigation;
- order search fill;
- open order click;
- formula tab click;
- review formula click.

`compiler_readiness = not_ready` means the preview is missing at least one required event. It is an advisory UI signal; the compiler remains the source of truth and still validates server-side before creating a skill.

## Test Result

The hardening baseline verification result was:

```text
python -m pytest
141 passed, 9 skipped, 2 warnings
```

For this evidence-freeze block, the expected verification command remains:

```bash
python -m pytest
```

## Known Skips

The known skips are browser-dependent paths in the plain shell test run when the Playwright browser runtime is not active for that environment.

These skips do not affect the TestClient evidence artifact, which exercises the API recording, compilation, and deterministic skill-run path without launching Chromium.

## Explicit Limitations

This is still not:

- real Odoo UI automation;
- a free recorder for arbitrary websites;
- a browser extension;
- an MCP integration;
- an LLM interpretation workflow;
- real ERP write execution;
- a marketplace or multi-ERP automation product.

The Fake ERP surface uses known `data-testid` selectors and constrained routes. The human recording flow is intentionally narrow so the compiler can validate it deterministically.

## Why This Is Not Odoo Real Or Free Recording

The recording target is the local Fake ERP demo surface, not a live Odoo instance.

The capture script only appears when Fake ERP pages receive a `recording_id`, and it only listens to known selectors in the formula review scenario. It does not observe arbitrary tabs, arbitrary domains, arbitrary ERP actions, or real ERP write operations.

The compiler recognizes only the Fake ERP formula review event contract. It does not infer intent from open-ended browsing and does not use an LLM to repair or generalize unknown flows.

## Recommended Next Block

The next block should stay narrow: add an operator-facing evidence/export view or a small negative-diagnostics demo panel that shows why incomplete recordings fail.

Do not expand to real Odoo, free-form recording, LLM repair, MCP, browser extensions, or ERP write actions until the controlled Fake ERP evidence and TFM narrative are fully stable.
