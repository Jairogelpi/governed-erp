# Operations Runbook

## Daily Health Check

```bash
sudo systemctl status erpguard --no-pager
journalctl -u erpguard -n 100 --no-pager
curl http://127.0.0.1:8000/v1/release/health
curl http://127.0.0.1:8000/v1/release/readiness-report
curl http://127.0.0.1:8000/v1/release/safety-boundaries
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

Expected:

```text
release health returns 200
readiness report returns 200
safety boundaries return 200
/demo returns 200 through ops_check
operator smoke returns a controlled result
```

## Restart

```bash
sudo systemctl restart erpguard
sudo systemctl status erpguard --no-pager
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

## Logs

```bash
journalctl -u erpguard -n 100 --no-pager
journalctl -u erpguard -f
```

Do not paste secrets into logs or issue comments. Release endpoints and ops scripts do not require private Odoo credentials.

## Data Directory

Persistent runtime data lives under:

```text
/var/lib/erpguard
/var/lib/erpguard/backups
```

The release SQLite path is:

```text
sqlite:////var/lib/erpguard/erpguard.db
```

## Safety Checks

```bash
curl http://127.0.0.1:8000/v1/release/safety-boundaries
```

Confirm:

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
ALLOW_R1_REAL_WRITE_PILOT=false
ALLOW_R2_REAL_WRITE_PILOT=false
```

## Incident Triage

If the service fails:

```bash
sudo systemctl status erpguard --no-pager
journalctl -u erpguard -n 200 --no-pager
cat /etc/erpguard/erpguard.env
ls -la /var/lib/erpguard
```

Check that `/opt/erpguard/.venv/bin/uvicorn` exists and that `/opt/erpguard/app` contains the repo.

If the app starts but health is degraded, run:

```bash
python scripts/ops_check.py --base-url http://127.0.0.1:8000 --skip-smoke
```
