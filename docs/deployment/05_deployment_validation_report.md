# Deployment Validation Report

## Scope

Sprint 14 validates the VPS operations contract for ERPGuard v0.12.0-rc1: systemd service definition, environment convention, persistent data path, logs, restart policy, backup workflow, update workflow, and post-deploy smoke validation.

This report records repository-side validation. A real VPS run should replace the placeholders with concrete server details and set status to `validated_on_vps`.

## Target Environment

```text
target OS or validation environment: local repository validation with VPS contract
Python version: Python 3.13.1
service mode tested: local script and contract validation; systemd unit reviewed as deployment asset
systemd status result or local fallback: local fallback, unit contract tested
final status: validated_locally_with_vps_contract
```

Valid status values:

```text
validated_on_vps
validated_locally_with_vps_contract
blocked_by_vps_access
blocked_by_service_error
blocked_by_dependency_error
```

## Commands Validated

```bash
python -m pytest tests/test_deployment_contract.py tests/test_ops_scripts_contract.py -q
python -m pytest
git diff --check
python scripts/ops_check.py --base-url http://127.0.0.1:8000
python scripts/backup_release_db.py --db-path <test-db> --backup-dir <test-backups>
```

Repository-side observed results:

```text
focused deployment contracts: 9 passed
backup script: created timestamped SQLite backup from a temporary database
ops_check against local uvicorn: passed (7/7)
```

## Release Health Result

```text
release health result: validated by existing release endpoint contract and ops_check path
GET /v1/release/health -> 200 in local uvicorn validation
```

## Readiness Result

```text
readiness result: validated by existing release endpoint contract and ops_check path
GET /v1/release/readiness-report -> 200 in local uvicorn validation
```

## Operator Smoke Result

```text
operator smoke result: validated by ops_check with controlled POST /v1/release/operator-smoke
POST /v1/release/operator-smoke -> 200 in local uvicorn validation
```

## Backup Result

```text
backup result: backup_release_db.py creates timestamped backup files and fails clearly when the DB file is missing
backup command: python scripts/backup_release_db.py
```

## Issues Found

```text
problem: release candidate had clean-install helpers but no VPS operations docs.
problem: no systemd unit existed for ERPGuard.
problem: no deployment environment example existed under deploy/env.
problem: no operations check script existed for deployed service validation.
problem: no release DB backup script existed.
problem: no update workflow script existed.
```

## Fixes Applied

```text
fix: added docs/deployment/00_vps_deployment.md.
fix: added docs/deployment/01_systemd_service.md.
fix: added docs/deployment/02_operations_runbook.md.
fix: added docs/deployment/03_backup_and_restore.md.
fix: added docs/deployment/04_update_procedure.md.
fix: added docs/deployment/05_deployment_validation_report.md.
fix: added deploy/systemd/erpguard.service.
fix: added deploy/env/erpguard.env.example.
fix: added scripts/ops_check.py.
fix: added scripts/backup_release_db.py.
fix: added scripts/update_release_candidate.sh.
```

## Safety Confirmation

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
ALLOW_R1_REAL_WRITE_PILOT=false
ALLOW_R2_REAL_WRITE_PILOT=false
```

No deployment doc or script enables generic writes, R3/R4 writes, or write pilots by default.

## Remaining VPS Steps

```text
Provision the target VPS.
Install OS packages.
Create the erpguard service user.
Install /etc/erpguard/erpguard.env.
Install /etc/systemd/system/erpguard.service.
Start the service.
Run python scripts/ops_check.py --base-url http://127.0.0.1:8000.
Run python scripts/backup_release_db.py.
Run sudo systemctl restart erpguard and re-run ops_check.
Update this report with actual VPS systemd status and endpoint outputs.
```
