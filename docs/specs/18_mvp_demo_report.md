# 18 MVP Demo Report

**Status:** Practical demo report and operator guide
**Date:** May 18, 2026
**Relationship to ERP Agent OS:** Freezes the current working MVP after Browser Recorder.
**Relationship to ERPGuard:** Shows how ERPGuard blocks unsafe data in the deterministic run path.

## Purpose

This document freezes the current end-to-end MVP in a form that can be demoed and operated.

The current working loop is:

Fake ERP Web
-> Browser Recorder
-> Recording Session
-> Recording-to-Skill Compiler
-> Skill Registry
-> Deterministic Skill Run
-> ERPGuard Formula Guard
-> token economics

## 1. MVP Status

The current MVP demonstrates the full path from an interactive ERP-like UI to a reusable guarded skill.

It proves that a browser interaction can be captured, compiled, registered, and replayed deterministically without LLM usage on the repeat path.

## 2. Current Implemented Endpoints

The following endpoints are currently implemented:

- GET /health
- GET /fake-erp/sales/orders
- GET /fake-erp/sales/orders/{order_id}
- GET /fake-erp/sales/orders/{order_id}/formula
- POST /v1/recordings/demo-fake-erp-formula-flow
- GET /v1/recordings/{recording_id}
- POST /v1/recordings/{recording_id}/compile-skill
- POST /v1/skills/{skill_id}/run
- GET /v1/skills/{skill_id}
- GET /v1/skills/{skill_id}/runs/{skill_run_id}
- POST /v1/skills/{skill_id}/run-ui

## 3. End-to-End Demo Script

### Step 1: start the API

```bash
uvicorn apps.api.main:app --reload
```

### Step 2: run browser demo recorder

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings/demo-fake-erp-formula-flow ^
  -H "Content-Type: application/json" ^
  -d "{\"base_url\":\"http://127.0.0.1:8000\",\"order_reference\":\"SO-FORMULA-MISMATCH\",\"actor\":{\"type\":\"user\",\"id\":\"user_1\",\"display_name\":\"Test User\"}}"
```

### Step 3: inspect the recording

```bash
curl http://127.0.0.1:8000/v1/recordings/{recording_id}
```

### Step 4: compile recording into skill

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings/{recording_id}/compile-skill ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Recorded Fake ERP Formula Review\",\"description\":\"Compiled from demo recording.\",\"runtime_type\":\"deterministic_browser\"}"
```

### Step 5: run compiled skill with valid order

```bash
curl -X POST http://127.0.0.1:8000/v1/skills/{skill_id}/run ^
  -H "Content-Type: application/json" ^
  -d "{\"inputs\":{\"order_reference\":\"SO-VALID\"}}"
```

Expected: allow.

### Step 6: run compiled skill with invalid order

```bash
curl -X POST http://127.0.0.1:8000/v1/skills/{skill_id}/run ^
  -H "Content-Type: application/json" ^
  -d "{\"inputs\":{\"order_reference\":\"SO-FORMULA-MISMATCH\"}}"
```

Expected: block.

### Step 7: inspect skill run

```bash
curl http://127.0.0.1:8000/v1/skills/{skill_id}/runs/{skill_run_id}
```

## 4. What This Proves

This MVP proves that:

- a browser interaction can be captured as structured recording events;
- the recording can be compiled into a reusable skill;
- the skill runs deterministically without LLM;
- ERPGuard blocks bad business data;
- repeated execution has repeated_execution_token_cost=0;
- audit and run steps are inspectable.

## 5. Current Limitations

The current MVP is intentionally narrow.

- Browser recorder is deterministic demo-only
- no free human recording yet
- no browser extension
- no LLM builder
- no MCP Gateway
- no real Odoo UI
- Playwright tests may skip if Chromium is not installed
- SQLite/Base.metadata MVP persistence, no Alembic yet
- token economics are hardcoded for MVP

## 6. How to Install Playwright Browser Binaries

If Chromium is not available, install it with:

```bash
python -m playwright install chromium
```

## 7. Test Status

Current known test status:

```text
139 passed
```

## 8. Next Recommended Implementation Block

The next recommended block is the Demo Orchestrator endpoint.

Target endpoint:

```http
POST /v1/demo/full-record-to-skill-flow
```

It should run:

demo recorder
-> compile skill
-> run skill with SO-VALID
-> run skill with SO-FORMULA-MISMATCH
-> return one consolidated report

Do not implement it yet in this documentation block.

## 9. Known Good Demo Run

- Date: May 18, 2026
- Endpoint used: `POST /v1/demo/full-record-to-skill-flow`
- Expected valid decision: allow
- Expected invalid decision: block
- Evidence file path: [docs/demo/full_record_to_skill_success_response.json](../demo/full_record_to_skill_success_response.json)