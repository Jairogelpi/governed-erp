# Backup And Restore

## Backup Purpose

Sprint 14 adds a backup workflow for the release SQLite database. It does not add new ERP behavior.

## Backup Command

From `/opt/erpguard/app`:

```bash
python scripts/backup_release_db.py
```

Default source:

```text
/var/lib/erpguard/erpguard.db
```

Default destination:

```text
/var/lib/erpguard/backups
```

The script creates timestamped files like:

```text
/var/lib/erpguard/backups/erpguard-YYYYMMDDTHHMMSSZ.db
```

You can override paths:

```bash
python scripts/backup_release_db.py --db-path /var/lib/erpguard/erpguard.db --backup-dir /var/lib/erpguard/backups
```

## Validate Backup

```bash
ls -lh /var/lib/erpguard/backups
sqlite3 /var/lib/erpguard/backups/erpguard-YYYYMMDDTHHMMSSZ.db ".tables"
```

## Restore Procedure

Stop service:

```bash
sudo systemctl stop erpguard
```

Copy backup into place:

```bash
sudo cp /var/lib/erpguard/backups/erpguard-YYYYMMDDTHHMMSSZ.db /var/lib/erpguard/erpguard.db
sudo chown erpguard:erpguard /var/lib/erpguard/erpguard.db
sudo chmod 640 /var/lib/erpguard/erpguard.db
```

Start service and validate:

```bash
sudo systemctl start erpguard
sudo systemctl status erpguard --no-pager
python scripts/ops_check.py --base-url http://127.0.0.1:8000
```

## Safety

Backups may contain local application data. Do not publish backup files. The backup script does not print secrets, and release validation does not require private Odoo credentials.
