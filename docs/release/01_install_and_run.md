# Install and Run

## Requirements

- Python 3.11+
- pip
- Git
- Bash on Linux/macOS or PowerShell on Windows

## Clean VPS Setup

```bash
git clone https://github.com/Jairogelpi/TFM.git
cd TFM
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

The default `.env.example` uses:

```text
ERPGUARD_DATABASE_URL=sqlite:///./erpguard_release_candidate.db
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
```

## Run the API with Release Script

Linux/macOS:

```bash
bash scripts/start_release_candidate.sh
```

Windows PowerShell:

```powershell
.\scripts\start_release_candidate.ps1
```

Script path: `scripts/start_release_candidate.ps1`.

Manual equivalent:

```bash
python -c "from erpguard.db.session import init_db; init_db()"
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

## Verify Release Endpoints

```bash
curl http://localhost:8000/v1/release/health
curl http://localhost:8000/v1/release/readiness-report
curl -X POST http://localhost:8000/v1/release/demo-seed
curl -X POST http://localhost:8000/v1/release/operator-smoke
curl http://localhost:8000/v1/release/safety-boundaries
```

Expected:

```json
{"status": "ok", "version": "0.12.0-rc1", "db_accessible": true, "safety_boundaries_locked": true}
```

Optional checker:

```bash
python scripts/check_release_install.py --base-url http://127.0.0.1:8000
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

Navigate to:

```text
http://localhost:8000/demo
```

For a VPS, replace `localhost` with the server IP:

```text
http://SERVER_IP:8000/demo
```

## Run smoke test

```bash
curl -X POST http://localhost:8000/v1/release/operator-smoke
```

## Safety Defaults

Sprint 13 validates installation only. It must keep:

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
ALLOW_R1_REAL_WRITE_PILOT=false
ALLOW_R2_REAL_WRITE_PILOT=false
```

Do not set real Odoo credentials for the release smoke path unless you are deliberately running a separate read-only adapter test.
