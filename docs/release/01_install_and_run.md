# Install and Run

## Requirements

- Python 3.11+
- pip

## Setup

```bash
git clone https://github.com/Jairogelpi/TFM.git
cd TFM
pip install -e ".[dev]"
```

## Run the API

```bash
uvicorn apps.api.main:app --reload --port 8000
```

## Verify

```bash
curl http://localhost:8000/v1/release/health
```

Expected:
```json
{"status": "ok", "version": "0.12.0-rc1", "db_accessible": true, "safety_boundaries_locked": true}
```

## Run tests

```bash
python -m pytest
```

## Seed demo data

```bash
curl -X POST http://localhost:8000/v1/release/demo-seed
```

## Open the dashboard

Navigate to `http://localhost:8000/demo`.

## Run smoke test

```bash
curl -X POST http://localhost:8000/v1/release/operator-smoke
```
