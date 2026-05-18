# 20 Demo Dashboard MVP

**Status:** Implementation spec for the minimal operator-facing demo dashboard
**Date:** May 18, 2026
**Relationship to ERP Agent OS:** Adds a thin visual surface over the current MVP so non-technical users can understand the loop.
**Relationship to ERPGuard:** Reuses the existing full demo orchestrator and Formula Guard path without adding new policy logic.

## Purpose

This document defines the smallest useful dashboard for the current Record-to-Skill MVP.

The dashboard is not the final ERP Agent OS web app.
It is a thin HTML surface over the existing backend so an operator, evaluator, or stakeholder can run the current MVP with one click and read the result.

The demo loop remains:

Fake ERP Web
-> Browser Recorder
-> Recording Session
-> Recording-to-Skill Compiler
-> Skill Registry
-> Deterministic Skill Run
-> ERPGuard Formula Guard
-> token economics

## 1. Product Purpose

The dashboard turns the API-only MVP into a visual demo surface.

It should make the current product loop understandable at a glance and allow a user to execute the complete flow from a browser page instead of manually wiring API calls.

## 2. User Journey

The expected journey is:

- user opens `/demo`
- user sees a short explanation of the ERP Agent OS MVP
- user clicks `Run full demo`
- dashboard calls `POST /v1/demo/full-record-to-skill-flow`
- dashboard renders success or controlled browser-unavailable error
- user sees allow/block result and token economics

## 3. UI Requirements

Create a simple HTML page, no full frontend framework required.

Suggested route:

```http
GET /demo
```

The page should show:

- title: `ERP Agent OS — Record-to-Skill MVP`
- short product explanation
- button: `Run full demo`
- section: `Flow`
- section: `Results`
- section: `Token Economics`
- section: `Proof`
- section: `Known Good Evidence`

## 4. Run Request Defaults

The dashboard should use these defaults:

```json
{
  "base_url": "http://127.0.0.1:8000",
  "record_order_reference": "SO-FORMULA-MISMATCH",
  "valid_order_reference": "SO-VALID",
  "invalid_order_reference": "SO-FORMULA-MISMATCH",
  "actor": {
    "type": "user",
    "id": "demo_user",
    "display_name": "Demo User"
  }
}
```

The base URL can be editable if easy, but the block must stay minimal.

## 5. Expected Success Rendering

On success, render:

- recording_id
- recording.status
- recording.event_count
- skill_id
- version_id
- skill name
- llm_required_for_repeated_runs
- valid run decision
- invalid run decision
- invalid issues_count
- creation_token_cost_estimate
- repeated_execution_token_cost
- estimated_tokens_saved_per_run
- total_estimated_tokens_saved
- proof.record_to_skill
- proof.deterministic_replay
- proof.erpguard_blocked_invalid_order
- proof.no_llm_used_for_repeated_runs

## 6. Expected Error Rendering

If the backend returns:

```json
{
  "error": {
    "code": "browser_runtime_unavailable",
    "message": "Playwright browser binaries are unavailable."
  }
}
```

the dashboard should show a clear message:

`Chromium is not installed. Run python -m playwright install chromium.`

## 7. Technical Implementation

Prefer minimal FastAPI HTML response.

Suggested files:

```text
apps/api/routes/demo_dashboard.py
tests/test_demo_dashboard.py
```

Register the route in:

```text
apps/api/main.py
```

Use vanilla HTML + JavaScript fetch.
Do not add React, Vite, Tailwind, or a separate frontend framework for this block.

## 8. Safety and Scope

The dashboard must only call the existing demo orchestrator.

It must not expose arbitrary ERP actions.
It must not allow custom browser automation.
It must not allow writes to real ERP systems.
It must not call LLMs.

## 9. Tests

Add:

```text
tests/test_demo_dashboard.py
```

Test:

- `GET /demo` returns 200
- page contains `ERP Agent OS`
- page contains `Record-to-Skill`
- page contains `Run full demo`
- page references `/v1/demo/full-record-to-skill-flow`
- health endpoint still works

If JavaScript does not execute in `TestClient`, do not test browser JS. Only test server-rendered HTML presence.

## 10. README Update

Add a short section:

```text
## Demo Dashboard
```

Include:

```bash
uvicorn apps.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/demo
```

Mention that Chromium must be installed for the live browser path:

```bash
python -m playwright install chromium
```

## 11. AGENTS Update

Record that the minimal `/demo` dashboard was added, that no LLM/MCP/Odoo UI/browser extension was introduced, and what the test result was.

## 12. Acceptance Criteria

- `/demo` loads
- dashboard can trigger the existing full MVP demo endpoint
- HTML clearly explains the current MVP loop
- no new backend orchestration logic is duplicated
- no LLM/MCP/browser extension/real Odoo UI code is added
- tests pass

If this block is complete, the MVP gains a clear operator-facing entry point without expanding scope beyond the current demo loop.