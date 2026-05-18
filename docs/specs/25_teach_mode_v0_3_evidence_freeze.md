# 25 Teach Mode v0.3 Evidence Freeze

**Status:** Evidence and documentation freeze
**Date:** May 18, 2026
**Baseline commit:** `10deeee feat: add teach mode v0.3 readiness`
**Evidence artifact:** `docs/demo/teach_mode_v0_3_success_response.json`

## Purpose

This document freezes the Teach Mode v0.3 evidence state after the readiness endpoint, shared analyzer, and `/demo` checklist were added.

This block is documentation and evidence only. It does not expand runtime scope, ERP coverage, automation capability, or UI architecture.

## Exact Teach Mode v0.3 State

Teach Mode v0.3 is a controlled Fake ERP teaching experience on top of Human Recording v0.2.1.

It includes:

- `GET /v1/recordings/{recording_id}/readiness`;
- shared `analyze_recording_readiness(recording, events)` logic;
- compiler reuse of the readiness contract before skill creation;
- `/demo` checklist for teaching the process step by step;
- readiness states for the required event evidence;
- deterministic skill replay after compilation;
- Formula Guard allow/block proof for `SO-VALID` and `SO-FORMULA-MISMATCH`.

## Problem Solved Compared To v0.2.1

Human Recording v0.2.1 already validated the minimum event sequence and exposed a preview/readiness JSON block.

Teach Mode v0.3 makes that evidence understandable as a teaching workflow. Instead of asking the operator to interpret raw selectors and event JSON, the UI and endpoint describe whether each expected process step has been observed or is missing.

The improvement is clarity, not automation breadth.

## Readiness Endpoint

The endpoint is:

```http
GET /v1/recordings/{recording_id}/readiness
```

It reads the stored `RecordingSession` and ordered `RecordingEvent` records, then returns the result of `analyze_recording_readiness`.

## Readiness Response Contract

The response shape is:

```json
{
  "recording_id": "recording_...",
  "status": "recording|finished|failed",
  "event_count": 5,
  "readiness": "ready|not_ready",
  "steps": [
    {"id": "sales_orders_navigation", "status": "observed|missing"},
    {"id": "order_search", "status": "observed|missing"},
    {"id": "open_order", "status": "observed|missing"},
    {"id": "formula_tab", "status": "observed|missing"},
    {"id": "review_formula", "status": "observed|missing"}
  ],
  "diagnostics": []
}
```

For complete recordings, `readiness = ready` and `diagnostics = []`.

For incomplete recordings, `readiness = not_ready`, at least one required step is `missing`, and `diagnostics` contains compiler-compatible messages such as:

- `missing_order_search_event`
- `missing_formula_tab_event`
- `missing_review_formula_event`

## Process States

Teach Mode uses these states:

- `pending`: the user has not reached this operator-facing process step yet;
- `observed`: the recording contains evidence for the required event step;
- `missing`: the readiness endpoint did not find required evidence;
- `ready`: all required event evidence is present and the recording can be compiled.

The server readiness endpoint returns `observed` or `missing` for the five required event steps. The `/demo` UI also uses `pending` and `ready` to represent the broader teaching workflow around recording, compiling, and running proof.

## Using Teach Mode From `/demo`

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/demo
```

Use the Teach Mode v0.3 flow:

1. Start recording
2. Open Fake ERP
3. Search order
4. Open order
5. Open formula tab
6. Review formula
7. Finish recording
8. Compile skill
9. Run allow/block proof

After finishing the recording, `/demo` calls the readiness endpoint and renders the observed/missing/ready state of the teaching checklist.

## Compiler Readiness Reuse

The compiler no longer owns a separate validation path for the supported Fake ERP formula flow.

`compile_recording_to_skill_package(recording, events)` calls `analyze_recording_readiness(recording, events)`.

If `readiness != ready`, compilation raises `ValueError` with the first diagnostic, preserving the existing API behavior:

```json
{
  "error": {
    "code": "unsupported_recording_flow",
    "message": "missing_order_search_event"
  }
}
```

If `readiness = ready`, the compiler creates the deterministic skill package as before.

## Evidence Artifact

The frozen evidence response is:

```text
docs/demo/teach_mode_v0_3_success_response.json
```

It was generated from a real FastAPI `TestClient` flow that:

- created a recording;
- added the five required events;
- queried readiness before finishing;
- verified `readiness = ready`;
- finished the recording;
- compiled the skill;
- ran `SO-VALID -> allow`;
- ran `SO-FORMULA-MISMATCH -> block`.

The artifact includes positive proof and negative readiness evidence.

## Negative Readiness Evidence

The evidence artifact records three incomplete recordings:

- missing `order_search` returns `not_ready` with `missing_order_search_event`;
- missing `formula_tab` returns `not_ready` with `missing_formula_tab_event`;
- missing `review_formula` returns `not_ready` with `missing_review_formula_event`.

These prove that Teach Mode can explain incomplete recordings without compiling them.

## Tests Performed

Teach Mode v0.3 added and preserved tests for:

- complete readiness returning `ready`;
- missing search returning `not_ready`;
- missing formula tab returning `not_ready`;
- missing review formula returning `not_ready`;
- compile success when readiness is ready;
- compile failure when readiness is not ready;
- `/demo` Teach Mode labels and step ids;
- health route;
- existing full demo orchestrator compatibility.

## Exact Pytest Result

The verification command is:

```bash
python -m pytest
```

Result for this evidence freeze:

```text
148 passed, 9 skipped, 2 warnings
```

## Known Skips

The skipped tests are browser-dependent paths in this shell because Chromium/Playwright browser runtime availability is not active for the plain `python -m pytest` run.

The Teach Mode evidence artifact uses FastAPI `TestClient`; it does not require launching Chromium.

## Limitations

Teach Mode v0.3 is intentionally narrow:

- it only supports the Fake ERP formula review flow;
- it depends on known Fake ERP selectors;
- it validates a fixed five-step event contract;
- it does not infer arbitrary user intent;
- it does not repair unknown recordings;
- it does not automate real ERP writes.

## No-Goals

This milestone did not add:

- real Odoo UI automation;
- MCP;
- LLM flow creation, interpretation, or repair;
- browser extension capture;
- unrestricted/free recording;
- marketplace behavior;
- frontend framework;
- real ERP write actions;
- architecture redesign.

It also did not change or break `POST /v1/demo/full-record-to-skill-flow`.

## Recommended Next Block

The next block should remain controlled and presentation-oriented.

Recommended next step:

```text
v0.3.1 Teach Mode diagnostics panel
```

That block could show missing-step explanations directly in `/demo` using the existing readiness diagnostics, without adding LLM, MCP, browser extension, real Odoo, free recording, marketplace, or real ERP write actions.
