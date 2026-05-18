# 24 Teach Mode v0.3

**Status:** Implementation spec for Teach Mode MVP
**Date:** May 18, 2026
**Baseline commits:** `9e2642e`, `e5061ef`
**Relationship to v0.2.1:** Converts the hardened controlled human recording flow into a clearer teaching experience without expanding automation scope.

## Purpose

Teach Mode v0.3 makes the existing Human Recording flow understandable as a guided "teach the process once" experience.

v0.2.1 proved that the compiler can validate a minimum controlled event sequence. Teach Mode uses that same validation contract to show the operator which steps have been observed, which are still missing, and whether the recording is ready to compile.

## User Flow

The user opens `/demo` and follows the Teach Mode steps:

1. Start recording
2. Open Fake ERP
3. Search order
4. Open order
5. Open formula tab
6. Review formula
7. Finish recording
8. Compile skill
9. Run allow/block proof

The first six steps are proven by recorded events. The last three are process states driven by the demo controls and API responses.

## Problem Solved Compared To v0.2.1

v0.2.1 exposed a preview/readiness JSON block, but the user still had to mentally map events and selectors back to the business process.

Teach Mode v0.3 turns the same evidence into a guided checklist. It makes incomplete recordings easier to understand without adding LLM interpretation, broad recording, or real ERP automation.

## Readiness Contract

The server exposes:

```http
GET /v1/recordings/{recording_id}/readiness
```

The response shape is:

```json
{
  "recording_id": "recording_...",
  "status": "recording|finished|failed",
  "event_count": 5,
  "readiness": "ready",
  "steps": [
    {"id": "sales_orders_navigation", "status": "observed"},
    {"id": "order_search", "status": "observed"},
    {"id": "open_order", "status": "observed"},
    {"id": "formula_tab", "status": "observed"},
    {"id": "review_formula", "status": "observed"}
  ],
  "diagnostics": []
}
```

For incomplete recordings, `readiness` is `not_ready`, missing steps use `status = "missing"`, and `diagnostics` contains compiler-compatible diagnostic messages such as `missing_order_search_event`.

The compiler must use the shared readiness analysis. If readiness is not `ready`, compilation continues to fail with the first existing diagnostic.

## Process States

Teach Mode uses these UI states:

- `pending`: the user has not reached this process step yet;
- `observed`: the recording contains the required event evidence;
- `missing`: the readiness endpoint says a required event is missing;
- `ready`: the recording contains all required event evidence and can be compiled.

The readiness endpoint uses only `observed` and `missing` for server-side event steps. `/demo` may use `pending` and `ready` for operator-facing workflow state.

## No-Goals

Teach Mode v0.3 must not add:

- real Odoo UI automation;
- MCP;
- LLM-based intent inference or repair;
- browser extension capture;
- unrestricted recording of arbitrary websites;
- real ERP write actions;
- marketplace behavior;
- a frontend framework;
- broad dashboard redesign;
- changes to `POST /v1/demo/full-record-to-skill-flow`.

The scope remains the controlled Fake ERP formula review scenario.

## Expected Tests

Tests must prove:

- readiness for a complete recording returns `ready`;
- readiness without search event returns `not_ready` and missing `order_search`;
- readiness without formula tab returns `not_ready` and missing `formula_tab`;
- readiness without review formula returns `not_ready` and missing `review_formula`;
- compile still succeeds when readiness is `ready`;
- compile still fails when readiness is `not_ready`;
- `/demo` contains `Teach Mode v0.3` and the expected step ids/text;
- `GET /health` still works.

## Acceptance Criteria

Teach Mode v0.3 is accepted when:

- `GET /v1/recordings/{recording_id}/readiness` returns the contracted shape;
- compiler and endpoint share the same readiness analysis instead of duplicating rules;
- `/demo` shows the nine Teach Mode steps with states using vanilla HTML and JavaScript;
- the current compile and full demo orchestrator endpoints remain compatible;
- README and AGENTS are updated;
- `python -m pytest` passes, with browser-dependent skips documented if present;
- no LLM, MCP, browser extension, real Odoo UI, free recorder, marketplace, frontend framework, or real ERP write action is introduced.
