# ERPGuard

ERPGuard is a semantic safety layer for ERP operations. This repository is currently in Phase 1: the Odoo Preflight Core backend foundation.

## Release Candidate v0.12.0-rc1

ERPGuard v0.12.0-rc1 is packaged as an operator release candidate.

Release validation endpoints:

- `GET /v1/release/health`
- `GET /v1/release/readiness-report`
- `POST /v1/release/demo-seed`
- `POST /v1/release/operator-smoke`
- `GET /v1/release/safety-boundaries`

Clean install helpers:

- [docs/release/01_install_and_run.md](docs/release/01_install_and_run.md)
- [docs/release/05_clean_install_vps_validation.md](docs/release/05_clean_install_vps_validation.md)
- [docs/release/06_release_fix_log.md](docs/release/06_release_fix_log.md)
- `.env.example`
- `scripts/check_release_install.py`
- `scripts/start_release_candidate.sh`
- `scripts/start_release_candidate.ps1`

Quick clean-install shape:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
bash scripts/start_release_candidate.sh
```

Then validate from another shell:

```bash
python scripts/check_release_install.py --base-url http://127.0.0.1:8000
```

Safety defaults remain locked:

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
```

## Current Demo Story

Implemented: record once in the Fake ERP demo, validate readiness, compile a reusable skill, inspect the compiled package, run it deterministically, and audit the resulting runs and steps.

Simulated: an approval gate that plans the critical `confirm_sales_order` action, and an approval decision simulation that records approve/reject evidence without executing ERP writes.

Not implemented: real Odoo UI automation, real ERP writes, a full approval workflow, browser-extension capture, MCP, or an LLM-driven builder.

The flow is intentionally small and defensible: record -> readiness -> compile -> inspect -> run -> audit -> safe plan -> simulated decision.

The core product evidence lives in the runtime features and frozen JSON artifacts, while the last two stages are simulation layers that demonstrate safety boundaries.

No real Odoo calls are made in this repository yet.

The MVP stops at a controlled demo and audit trail.

The next step after this story is consolidation, not more feature growth.

This README is written to explain what exists today, what is simulated for the demo, and what remains intentionally out of scope.

## Next Phase Candidate

The next possible phase is `v0.8`, framed as a real Odoo read-only adapter plus an Odoo preflight demo.

That phase should stay narrow: connect to Odoo, read a real sales order, map it to the canonical model, run Formula Guard, and show an audited result.

It should not confirm orders, write records, or expand into a broader automation platform.

If pursued, it should be treated as a separate phase with its own evidence freeze and acceptance criteria.

## Sprint 1 - Real Odoo Connection & Diagnosis

This sprint adds the first real Odoo-facing capability: a read-only connection test and diagnosis flow.

The API-first entry points are:

- `POST /v1/odoo/connections`
- `POST /v1/odoo/connections/{connection_id}/test`
- `POST /v1/odoo/connections/{connection_id}/diagnose`
- `GET /v1/odoo/connections/{connection_id}/sales-orders/{order_reference}/raw-summary`

The flow validates credentials, reads the Odoo version and uid, inspects modules/models/fields, detects custom fields, reads limited samples, and returns a read-only diagnosis.

Read-only mode is enforced in code: no Odoo write methods are allowed in this sprint.

Secrets are redacted in API responses.

This sprint is the first practical bridge from the controlled Fake ERP MVP toward the real Odoo preflight phase.

## Local Setup

Create and activate a virtual environment, then install the project in editable mode:

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -e ".[dev]"
```

Run tests:

```bash
python -m pytest
```

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/health
```

Create a connection:

```bash
curl -X POST http://127.0.0.1:8000/v1/connections ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Odoo Test\",\"erp_type\":\"odoo\",\"config\":{\"url\":\"https://example.odoo.com\",\"database\":\"example-db\",\"username\":\"user@example.com\",\"api_key\":\"secret\"}}"
```

Responses redact `api_key`. Do not commit real Odoo credentials to Git.

Run preflight using a stored connection:

```bash
curl -X POST http://127.0.0.1:8000/v1/preflight ^
  -H "Content-Type: application/json" ^
  -d "{\"connection_id\":\"conn_...\",\"actor\":{\"type\":\"user\",\"native_user_id\":\"6\",\"display_name\":\"Test User\"},\"action\":{\"canonical_action\":\"confirm_sales_order\",\"canonical_object\":\"SalesOrder\",\"native\":{\"model\":\"sale.order\",\"method\":\"action_confirm\",\"record_id\":\"so_formula_mismatch\"}},\"options\":{\"simulate\":true,\"allow_write\":false},\"policy_id\":\"formula_guard\"}"
```

The older `erp_type: "fake"` preflight request is still supported for local development, but `connection_id` is the recommended flow.

Retrieve preflight evidence:

```bash
curl http://127.0.0.1:8000/v1/preflight/pf_...
```

Retrieve the audit trail:

```bash
curl http://127.0.0.1:8000/v1/audit/pf_...
```

Create a skill in the Skill Registry:

```bash
curl -X POST http://127.0.0.1:8000/v1/skills ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Safe Formula Guard UI Preflight\",\"description\":\"Validates a sales order formula through the Fake ERP flow.\",\"runtime_type\":\"deterministic_browser\",\"llm_required_for_repeated_runs\":false,\"skill_package\":{\"skill_id\":\"safe_formula_guard_ui_preflight\",\"inputs\":{\"order_reference\":\"string\"},\"guards\":[\"formula_guard\"],\"workflow\":[{\"id\":\"open_orders\",\"type\":\"navigate\",\"target\":\"/fake-erp/sales/orders\"},{\"id\":\"search_order\",\"type\":\"fill\",\"selector\":\"[data-testid='order-search']\"},{\"id\":\"open_order\",\"type\":\"click\",\"selector_template\":\"[data-testid='open-order-{{order_reference}}']\"},{\"id\":\"open_formula\",\"type\":\"click\",\"selector\":\"[data-testid='formula-tab']\"},{\"id\":\"review_formula\",\"type\":\"guard\",\"guard\":\"formula_guard\"}]}}"
```

List skills:

```bash
curl http://127.0.0.1:8000/v1/skills
```

Get a skill by id:

```bash
curl http://127.0.0.1:8000/v1/skills/skill_...
```

Run a skill:

```bash
curl -X POST http://127.0.0.1:8000/v1/skills/skill_.../run ^
  -H "Content-Type: application/json" ^
  -d "{\"inputs\":{\"order_reference\":\"SO-FORMULA-MISMATCH\"}}"
```

The repeated run path is deterministic and does not use the LLM.

Run the browser UI runtime:

```bash
curl -X POST http://127.0.0.1:8000/v1/skills/skill_.../run-ui ^
  -H "Content-Type: application/json" ^
  -d "{\"inputs\":{\"order_reference\":\"SO-FORMULA-MISMATCH\"},\"runtime\":{\"base_url\":\"http://127.0.0.1:8000\"}}"
```

Create a recording session:

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Review order formula from Fake ERP\",\"description\":\"User demonstrates how to open a sales order and review formula data.\",\"erp_type\":\"fake\",\"target_base_url\":\"http://127.0.0.1:8000\",\"actor\":{\"type\":\"user\",\"id\":\"user_1\",\"display_name\":\"Test User\"}}"
```

Add a recording event:

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings/recording_.../events ^
  -H "Content-Type: application/json" ^
  -d "{\"event_type\":\"click\",\"url\":\"http://127.0.0.1:8000/fake-erp/sales/orders\",\"page_title\":\"Fake ERP Sales Orders\",\"element_role\":\"link\",\"element_text\":\"Open SO-FORMULA-MISMATCH\",\"selector\":\"[data-testid='open-order-SO-FORMULA-MISMATCH']\",\"before_text_snapshot\":\"Sales Orders...\",\"after_text_snapshot\":\"Order SO-FORMULA-MISMATCH...\"}"
```

Compile a recording into a skill:

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings/recording_.../compile-skill ^
  -H "Content-Type: application/json" ^
  -d "{\"name\":\"Recorded Fake ERP Formula Review\",\"description\":\"Compiled from a demonstrated Fake ERP formula review flow.\",\"runtime_type\":\"deterministic_browser\"}"
```

Run the demo recorder:

```bash
curl -X POST http://127.0.0.1:8000/v1/recordings/demo-fake-erp-formula-flow ^
  -H "Content-Type: application/json" ^
  -d "{\"base_url\":\"http://127.0.0.1:8000\",\"order_reference\":\"SO-FORMULA-MISMATCH\",\"actor\":{\"type\":\"user\",\"id\":\"user_1\",\"display_name\":\"Test User\"}}"
```

Run the full MVP demo orchestrator:

```bash
curl -X POST http://127.0.0.1:8000/v1/demo/full-record-to-skill-flow ^
  -H "Content-Type: application/json" ^
  -d "{\"base_url\":\"http://127.0.0.1:8000\",\"record_order_reference\":\"SO-FORMULA-MISMATCH\",\"valid_order_reference\":\"SO-VALID\",\"invalid_order_reference\":\"SO-FORMULA-MISMATCH\",\"actor\":{\"type\":\"user\",\"id\":\"user_1\",\"display_name\":\"Test User\"}}"
```

## Full MVP Demo Evidence

The known-good end-to-end response is stored at [docs/demo/full_record_to_skill_success_response.json](docs/demo/full_record_to_skill_success_response.json).

## Demo Dashboard

Start the API:

```bash
uvicorn apps.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/demo
```

If you want the live browser path to run, install Chromium first:

```bash
python -m playwright install chromium
```

## Human Recording v0.2

Start the API and open the demo dashboard:

```bash
uvicorn apps.api.main:app --reload
```

Then open:

```text
http://127.0.0.1:8000/demo
```

Use the Human Recording v0.2 controls to:

- start a controlled recording session
- open the Fake ERP sales orders page
- perform the formula review flow manually
- finish the recording
- compile it into a skill
- run the compiled skill for `SO-VALID` and `SO-FORMULA-MISMATCH`

The controlled browser path only works when Chromium is installed:

```bash
python -m playwright install chromium
```

## Human Recording v0.2.1 Hardening

The `/demo` dashboard now shows a human recording preview after finish:

- `recording_id`
- recording status
- event count
- ordered event summaries
- captured selectors
- compiler readiness: `ready` or `not_ready`

The recording-to-skill compiler also validates the minimum controlled Fake ERP sequence before creating a skill, so incomplete recordings return clear diagnostics such as `missing_order_search_event`, `missing_formula_tab_event`, or `missing_review_formula_event`.

## Human Recording v0.2.1 Evidence

The frozen v0.2.1 evidence response is stored at [docs/demo/human_recording_v0_2_1_success_response.json](docs/demo/human_recording_v0_2_1_success_response.json).

It was generated from a FastAPI `TestClient` flow that creates a controlled recording, posts the five required Fake ERP events, compiles the recording, and runs the compiled skill for `SO-VALID` and `SO-FORMULA-MISMATCH`.

Verify the current evidence baseline with:

```bash
python -m pytest
```

Expected result for the v0.2.1 evidence freeze environment:

```text
141 passed, 9 skipped, 2 warnings
```

## Teach Mode v0.3

Teach Mode v0.3 keeps the same controlled Fake ERP formula review flow, but renders it as a teach-the-process checklist in `/demo`.

The dashboard now shows the expected teaching steps from start recording through allow/block proof, and uses the readiness API to mark recorded evidence as `observed`, `missing`, or `ready`.

Inspect readiness for a recording:

```bash
curl http://127.0.0.1:8000/v1/recordings/recording_.../readiness
```

The response reports:

- `readiness`: `ready` or `not_ready`
- `event_count`
- step status for `sales_orders_navigation`, `order_search`, `open_order`, `formula_tab`, and `review_formula`
- compiler-compatible diagnostics for missing steps

This is still a controlled Fake ERP demo path. It is not real Odoo UI automation, a browser extension, a free recorder, or an LLM-based flow builder.

## Teach Mode v0.3 Evidence

The frozen Teach Mode v0.3 evidence response is stored at [docs/demo/teach_mode_v0_3_success_response.json](docs/demo/teach_mode_v0_3_success_response.json).

It was generated from a FastAPI `TestClient` flow that creates a controlled recording, adds the five required events, checks readiness, finishes the recording, compiles the skill, and runs `SO-VALID -> allow` plus `SO-FORMULA-MISMATCH -> block`.

Verify the current evidence baseline with:

```bash
python -m pytest
```

Expected result for the Teach Mode v0.3 evidence freeze environment:

```text
148 passed, 9 skipped, 2 warnings
```

## Skill Inspector v0.4

After compiling a skill, inspect the latest version before trusting repeated runs:

```bash
curl http://127.0.0.1:8000/v1/skills/skill_.../inspect
```

The inspector shows the skill name, version, runtime type, inputs, guards, workflow steps, the originating recording id, and a safety summary. The `/demo` dashboard renders the same Skill Inspector v0.4 section automatically after compilation and again after the proof run.

## Skill Inspector v0.4 Evidence

The frozen Skill Inspector v0.4 evidence response is stored at [docs/demo/skill_inspector_v0_4_success_response.json](docs/demo/skill_inspector_v0_4_success_response.json).

It was generated from a FastAPI `TestClient` flow that creates a controlled recording, posts the five required Fake ERP events, checks readiness, finishes the recording, compiles the skill, inspects the compiled skill, and runs `SO-VALID -> allow` plus `SO-FORMULA-MISMATCH -> block`.

Verify the current evidence baseline with:

```bash
python -m pytest
```

Expected result for the Skill Inspector v0.4 evidence freeze environment:

```text
151 passed, 9 skipped
```

The evidence artifact also includes negative controlled error responses for a missing skill and a skill with no latest version.

## Run History / Audit Timeline v0.5

After a compiled skill has been run, inspect the execution history and audit timeline:

```bash
curl http://127.0.0.1:8000/v1/skills/skill_.../runs
curl http://127.0.0.1:8000/v1/skills/skill_.../runs/skill_run_.../timeline
```

The run list shows each execution with its decision, timestamps, input, summary output, and token savings. The timeline shows the ordered `load_skill`, `load_order`, `formula_guard`, and `produce_result` steps so you can audit what happened in a replay.

## Run History / Audit Timeline v0.5 Evidence

The v0.5 evidence freeze captures the live FastAPI `TestClient` proof for the run history and audit timeline layer.

Artifact:

- [docs/demo/run_history_audit_timeline_v0_5_success_response.json](docs/demo/run_history_audit_timeline_v0_5_success_response.json)

It records:

- recording readiness in the ready state;
- skill compilation and inspection;
- a valid run that returns `allow`;
- an invalid run that returns `block`;
- `GET /v1/skills/{skill_id}/runs` returning both runs;
- `GET /v1/skills/{skill_id}/runs/{skill_run_id}/timeline` returning the ordered guard timeline;
- controlled `skill_not_found` and `skill_run_not_found` error responses.

Verification command:

```bash
python -m pytest
```

Observed result:

```text
155 passed, 9 skipped
```

## Approval Gate / Safe Action Plan v0.6

The approval gate adds a dry-run planning endpoint for the critical `confirm_sales_order` action:

```http
POST /v1/skills/{skill_id}/plan-action
```

Request example:

```json
{
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "requested_action": "confirm_sales_order"
}
```

The endpoint does not execute `confirm_sales_order`, does not write to ERP, and does not create a full approval system yet. It only returns a safe plan, the Formula Guard preview, the R3 approval requirement, and proof that execution stopped before any real write.

The `/demo` page includes an Approval Gate / Safe Action Plan v0.6 panel after compile and inspect, so the operator can preview the critical action before trusting it.

## Approval Gate / Safe Action Plan v0.6 Evidence

The v0.6 evidence freeze captures the live FastAPI `TestClient` proof for the approval gate dry-run layer.

Artifact:

- [docs/demo/approval_gate_safe_action_plan_v0_6_success_response.json](docs/demo/approval_gate_safe_action_plan_v0_6_success_response.json)

It records:

- dry-run approval planning for `confirm_sales_order`;
- `approval_required = true` and `risk_level = R3`;
- Formula Guard preview for `SO-VALID` returning `allow`;
- Formula Guard preview for `SO-FORMULA-MISMATCH` returning `block`;
- no `SkillRun` rows created by the planning endpoint;
- controlled `unsupported_action` and `skill_not_found` errors.

Verification command:

```bash
python -m pytest
```

Observed result:

```text
159 passed, 9 skipped
```

## Approval Decision Simulation v0.7

The approval decision simulation endpoint lets you simulate a human approve/reject choice for the critical `confirm_sales_order` path without executing a real ERP write:

```http
POST /v1/skills/{skill_id}/simulate-approval-decision
```

Request example:

```json
{
  "inputs": {
    "order_reference": "SO-VALID"
  },
  "requested_action": "confirm_sales_order",
  "decision": "approve",
  "approver": {
    "type": "user",
    "id": "demo_approver",
    "display_name": "Demo Approver"
  },
  "reason": "Formula preview is clean."
}
```

The endpoint reuses the same critical-action identity, risk level, and Formula Guard preview as v0.6, but it still does not execute `confirm_sales_order`, does not create a real approval workflow, and does not write to ERP.

The `/demo` page includes an Approval Decision Simulation v0.7 panel with simulate-approve and simulate-reject buttons after the safe plan section.

Verification command:

```bash
python -m pytest
```

Observed result:

```text
162 passed, 9 skipped
```

## Optional Odoo Smoke Read

The smoke script is manual only and is not part of the test suite. Set real credentials in your shell, then run:

```bash
set ODOO_URL=https://example.odoo.com
set ODOO_DB=example-db
set ODOO_USERNAME=user@example.com
set ODOO_API_KEY=your-api-key
python scripts/odoo_smoke_read.py
```

It authenticates, prints the Odoo version, and reads one `sale.order` summary without printing secrets.

## Current Scope

Implemented now:

- FastAPI app startup
- `GET /health`
- connection API with redacted secrets
- configuration module
- SQLAlchemy database base/session setup
- initial database models
- fake adapter demo path
- fake ERP web demo surface
- skill registry MVP
- deterministic Skill Run endpoint
- Playwright browser runtime for Fake ERP
- Recording Session API
- Browser Recorder MVP for Fake ERP
- Demo orchestrator endpoint for the current full MVP loop
- Controlled Human Recording v0.2 for the Fake ERP formula review flow
- Controlled Human Recording v0.2.1 hardening with compiler diagnostics and `/demo` preview/readiness
- Teach Mode v0.3 readiness endpoint and `/demo` checklist for the controlled Fake ERP teaching flow
- Skill Inspector v0.4 read-only inspection for compiled Fake ERP skills
- Skill Inspector v0.4 evidence freeze and JSON artifact
- read-only Odoo adapter skeleton
- Formula Guard policy evaluation for `confirm_sales_order`
- preflight persistence and audit retrieval
- minimal centralized risk semantics for canonical action defaults
- pytest foundation

Not implemented yet:

- UI
- LLM features
- ERP write/execution actions
- approval submission flow
- stock/manufacturing simulation
