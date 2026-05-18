# ERPGuard

ERPGuard is a semantic safety layer for ERP operations. This repository is currently in Phase 1: the Odoo Preflight Core backend foundation.

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
