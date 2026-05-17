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

## Current Scope

Implemented now:

- FastAPI app startup
- `GET /health`
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
