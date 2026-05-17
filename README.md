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
- pytest foundation

Not implemented yet:

- Odoo adapter
- Formula Guard
- policy evaluation
- UI
- LLM features
- ERP write/execution actions
