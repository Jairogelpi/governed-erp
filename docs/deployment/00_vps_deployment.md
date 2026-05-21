# VPS Deployment

## Purpose

Sprint 14 turns ERPGuard v0.12.0-rc1 into an operable VPS service. This is deployment and operations hardening only.

It does not add ERP features, new write capability, R3/R4 writes, generic writes, MCP execution gateway, browser automation, Kubernetes, or multi-node deployment.

## Target Flow

```text
Provision VPS
-> install OS packages
-> clone repo
-> create app user
-> configure persistent data directory
-> configure environment file
-> install Python dependencies
-> install systemd service
-> start service
-> check logs
-> run release health
-> run operator smoke
-> create backup
-> test restart
-> document update procedure
-> produce deployment validation report
```

## Recommended Paths

```text
/opt/erpguard/app          # cloned repo
/opt/erpguard/.venv        # Python virtualenv
/var/lib/erpguard          # persistent runtime data
/var/lib/erpguard/backups  # backups
/etc/erpguard/erpguard.env # environment config
/etc/systemd/system/erpguard.service
```

Recommended service user:

```text
erpguard
```

Recommended port:

```text
8000
```

## OS Packages

Ubuntu/Debian example:

```bash
sudo apt-get update
sudo apt-get install -y git python3 python3-venv python3-pip curl
```

## User And Directories

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin erpguard
sudo mkdir -p /opt/erpguard /var/lib/erpguard/backups /etc/erpguard
sudo chown -R erpguard:erpguard /opt/erpguard /var/lib/erpguard
```

## Clone And Install

```bash
sudo -u erpguard git clone https://github.com/Jairogelpi/TFM.git /opt/erpguard/app
sudo -u erpguard python3 -m venv /opt/erpguard/.venv
sudo -u erpguard /opt/erpguard/.venv/bin/python -m pip install --upgrade pip
sudo -u erpguard /opt/erpguard/.venv/bin/python -m pip install -e "/opt/erpguard/app[dev]"
```

## Configure Environment

```bash
sudo cp /opt/erpguard/app/deploy/env/erpguard.env.example /etc/erpguard/erpguard.env
sudo chown root:erpguard /etc/erpguard/erpguard.env
sudo chmod 640 /etc/erpguard/erpguard.env
```

The environment file keeps:

```text
ALLOW_GENERIC_REAL_ODOO_WRITES=false
ALLOW_R3_R4_REAL_WRITES=false
ALLOW_R1_REAL_WRITE_PILOT=false
ALLOW_R2_REAL_WRITE_PILOT=false
```

## Install systemd Service

```bash
sudo cp /opt/erpguard/app/deploy/systemd/erpguard.service /etc/systemd/system/erpguard.service
sudo systemctl daemon-reload
sudo systemctl enable erpguard
sudo systemctl start erpguard
```

## Validate

```bash
sudo systemctl status erpguard --no-pager
journalctl -u erpguard -n 100 --no-pager
curl http://127.0.0.1:8000/v1/release/health
curl -X POST http://127.0.0.1:8000/v1/release/operator-smoke
python /opt/erpguard/app/scripts/ops_check.py --base-url http://127.0.0.1:8000
```

Open:

```text
http://SERVER_IP:8000/demo
```

## Related Docs

- [01_systemd_service.md](01_systemd_service.md)
- [02_operations_runbook.md](02_operations_runbook.md)
- [03_backup_and_restore.md](03_backup_and_restore.md)
- [04_update_procedure.md](04_update_procedure.md)
- [05_deployment_validation_report.md](05_deployment_validation_report.md)
