# systemd Service

## Unit File

The service unit lives at:

```text
deploy/systemd/erpguard.service
```

Install it to:

```text
/etc/systemd/system/erpguard.service
```

The unit runs as the non-root `erpguard` user, loads `/etc/erpguard/erpguard.env`, starts `uvicorn apps.api.main:app`, writes logs to journald, and uses `Restart=always`.

## Install

```bash
sudo cp /opt/erpguard/app/deploy/systemd/erpguard.service /etc/systemd/system/erpguard.service
sudo systemctl daemon-reload
sudo systemctl enable erpguard
sudo systemctl start erpguard
```

## Service Commands

```bash
sudo systemctl status erpguard --no-pager
sudo systemctl restart erpguard
sudo systemctl stop erpguard
sudo systemctl start erpguard
journalctl -u erpguard -n 100 --no-pager
journalctl -u erpguard -f
```

## Expected Runtime

```text
WorkingDirectory=/opt/erpguard/app
EnvironmentFile=/etc/erpguard/erpguard.env
ExecStart=/opt/erpguard/.venv/bin/uvicorn apps.api.main:app --host 0.0.0.0 --port 8000
```

## Validation

```bash
curl http://127.0.0.1:8000/v1/release/health
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

## Safety

The systemd service must not override these safe defaults:

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
ALLOW_R1_REAL_WRITE_PILOT=false
ALLOW_R2_REAL_WRITE_PILOT=false
```
