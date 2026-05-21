# Clean Install VPS Validation

## Purpose

Sprint 13 validates ERPGuard v0.12.0-rc1 from a clean Linux VPS or fresh machine using only the GitHub repository, release documentation, and the `/v1/release/*` endpoints.

This validation is release hardening only. It does not add ERP capability, new write categories, browser automation, marketplace behavior, or high-risk real write execution.

## Target Flow

```text
Fresh VPS or clean machine
-> install system dependencies
-> clone repo
-> create Python environment
-> install project dependencies
-> configure environment
-> initialize DB
-> start API
-> call release endpoints
-> open /demo
-> run operator demo flow
-> document/fix friction
-> produce VPS validation report
```

## Machine/OS

Validation target:

```text
machine/OS: clean Linux VPS or fresh local machine
Python version: Python 3.11 or newer
release version: ERPGuard v0.12.0-rc1
final status: validated_with_fixes
```

The current repository-side validation was executed from the development workstation after adding the clean-install artifacts. A real VPS run should replace the machine/OS and Python version lines above with the concrete host details.

## Clean Install Commands

```bash
git clone https://github.com/Jairogelpi/TFM.git
cd TFM
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -e ".[dev]"
cp .env.example .env
```

Initialize the database and start the API:

```bash
bash scripts/start_release_candidate.sh
```

Equivalent manual command:

```bash
python -c "from erpguard.db.session import init_db; init_db()"
uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

Windows PowerShell equivalent:

```powershell
.\scripts\start_release_candidate.ps1
```

## Release Endpoint Results

Validate each endpoint from another shell:

```bash
curl http://127.0.0.1:8000/v1/release/health
curl http://127.0.0.1:8000/v1/release/readiness-report
curl -X POST http://127.0.0.1:8000/v1/release/demo-seed
curl -X POST http://127.0.0.1:8000/v1/release/operator-smoke
curl http://127.0.0.1:8000/v1/release/safety-boundaries
```

Expected release endpoint results:

```text
GET  /v1/release/health            -> 200, status ok or controlled degraded
GET  /v1/release/readiness-report  -> 200
POST /v1/release/demo-seed         -> 200
POST /v1/release/operator-smoke    -> 200, passed or controlled blocked-with-reasons
GET  /v1/release/safety-boundaries -> 200
```

The helper can check local files and, when the API is running, endpoint status:

```bash
python scripts/check_release_install.py --base-url http://127.0.0.1:8000
```

## Demo UI Result

Open:

```text
http://SERVER_IP:8000/demo
```

Expected demo UI result:

```text
GET /demo -> 200
Release Candidate panel visible
release health/readiness/demo seed/operator smoke/safety boundary controls visible
```

## Smoke Test Result

Run:

```bash
curl -X POST http://127.0.0.1:8000/v1/release/operator-smoke
```

Expected smoke test result:

```text
operator smoke returns 200
smoke_status is passed, partial, or failed with controlled checks
no private Odoo credentials required
no real ERP write execution enabled
```

## Issues Found

```text
problem: Sprint 12 docs did not yet include a dedicated clean VPS validation report.
problem: Startup commands existed in prose but not as one-command release helper scripts.
problem: .env.example used the generic local database filename instead of the release candidate filename.
problem: There was no repository-local checker for release docs and endpoint availability.
```

## Fixes Applied

```text
fix: added this clean install VPS validation document.
fix: added docs/release/06_release_fix_log.md.
fix: updated .env.example with release candidate DB path and false write flags.
fix: added scripts/check_release_install.py.
fix: added scripts/start_release_candidate.sh.
fix: added scripts/start_release_candidate.ps1.
fix: updated docs/release/01_install_and_run.md with clean venv, DB init, scripts, and endpoint checks.
```

## Remaining Manual Steps

```text
Run the same flow on the target VPS.
Record actual machine/OS and Python version.
Record endpoint responses in this document or in the release issue.
Confirm firewall/security group allows port 8000 only for the intended demo audience.
Stop the API after the validation session if the VPS is temporary.
```

## Safety Validation

The release remains locked by default:

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
ALLOW_R1_REAL_WRITE_PILOT=false
ALLOW_R2_REAL_WRITE_PILOT=false
can_execute_real_writes=false
```

The release validation confirms:

- generic modifications remain disabled;
- high-risk business operations remain disabled;
- R1/R2 pilots remain feature-flagged;
- release endpoints do not print secrets;
- demo seed does not require private credentials;
- operator smoke can run without real Odoo credentials through controlled local evidence.

## Final Status

```text
final status: validated_with_fixes
```

## Repository-Side Validation Run

The Sprint 13 repository-side validation run was executed on:

```text
machine/OS: Microsoft Windows 11 Home 10.0.26200, 64-bit
Python version: Python 3.13.1
install command used: python -m pip install -e ".[dev]"
test command used: python -m pytest
test result: 595 passed, 2 warnings
API startup command used: uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
release endpoint results: all required release endpoints returned 200
demo UI result: GET /demo returned 200
smoke test result: POST /v1/release/operator-smoke returned 200 with smoke_status=passed
helper check result: python scripts/check_release_install.py --base-url http://127.0.0.1:8000 -> passed (14/14)
final status: validated_with_fixes
```

This is not a substitute for the target Linux VPS run. It proves the repository contracts, scripts, and release endpoints are coherent before the VPS operator repeats the flow on a clean server.
