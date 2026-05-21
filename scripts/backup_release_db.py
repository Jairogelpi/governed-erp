from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote, urlparse


DEFAULT_BACKUP_DIR = Path(os.environ.get("ERPGUARD_BACKUP_DIR", "/var/lib/erpguard/backups"))


def sqlite_url_to_path(value: str | None) -> Path | None:
    if not value:
        return None
    if not value.startswith("sqlite:///"):
        return None

    parsed = urlparse(value)
    if parsed.netloc:
        return Path(f"//{parsed.netloc}{unquote(parsed.path)}")
    return Path(unquote(parsed.path))


def default_db_path() -> Path:
    explicit = os.environ.get("ERPGUARD_DATABASE_URL") or os.environ.get("ERPGUARD_DB_URL")
    parsed = sqlite_url_to_path(explicit)
    if parsed is not None:
        return parsed
    return Path("/var/lib/erpguard/erpguard.db")


def backup_database(db_path: Path, backup_dir: Path) -> Path:
    if not db_path.exists():
        raise FileNotFoundError(f"database file not found: {db_path}")

    backup_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_dir / f"erpguard-{timestamp}.db"
    shutil.copy2(db_path, destination)
    return destination


def main() -> int:
    parser = argparse.ArgumentParser(description="Back up the ERPGuard release SQLite database.")
    parser.add_argument("--db-path", default=None, help="SQLite database file path. Defaults to ERPGUARD_DATABASE_URL or /var/lib/erpguard/erpguard.db.")
    parser.add_argument("--backup-dir", default=str(DEFAULT_BACKUP_DIR), help="Backup output directory.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    db_path = Path(args.db_path) if args.db_path else default_db_path()
    backup_dir = Path(args.backup_dir)
    try:
        backup_path = backup_database(db_path, backup_dir)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    result = {
        "status": "backed_up",
        "db_path": str(db_path),
        "backup_path": str(backup_path),
    }
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Backup created: {backup_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
