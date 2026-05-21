# Update Procedure

## Purpose

This procedure updates the VPS service to the latest `origin/main`, reinstalls editable dependencies, restarts `erpguard`, and runs post-update smoke validation.

It does not enable new ERP capabilities or write pilots.

## Scripted Update

From a shell with sudo rights:

```bash
sudo -u erpguard APP_DIR=/opt/erpguard/app PYTHON_BIN=/opt/erpguard/.venv/bin/python bash /opt/erpguard/app/scripts/update_release_candidate.sh
```

The script performs:

```text
cd /opt/erpguard/app
git pull origin main
/opt/erpguard/.venv/bin/python -m pip install -e ".[dev]"
sudo systemctl restart erpguard
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

## Manual Update

```bash
cd /opt/erpguard/app
sudo -u erpguard git pull origin main
sudo -u erpguard /opt/erpguard/.venv/bin/python -m pip install -e ".[dev]"
sudo systemctl restart erpguard
sudo systemctl status erpguard --no-pager
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

## Pre-Update Backup

```bash
python scripts/backup_release_db.py
```

## Post-Update Validation

```bash
curl http://127.0.0.1:8000/v1/release/health
curl http://127.0.0.1:8000/v1/release/readiness-report
curl -X POST http://127.0.0.1:8000/v1/release/operator-smoke
curl http://127.0.0.1:8000/v1/release/safety-boundaries
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

Confirm:

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
```

## Rollback

If the update fails:

```bash
cd /opt/erpguard/app
git log --oneline -5
git checkout <previous-known-good-commit>
/opt/erpguard/.venv/bin/python -m pip install -e ".[dev]"
sudo systemctl restart erpguard
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

Restore a DB backup only if data corruption is confirmed.
