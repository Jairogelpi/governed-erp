from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_ops_check_help_imports_cleanly_and_mentions_release_endpoints():
    script = ROOT / "scripts" / "ops_check.py"
    assert script.exists()

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "operations check" in result.stdout.lower()
    assert "--base-url" in result.stdout


def test_backup_release_db_creates_timestamped_backup_without_secrets(tmp_path):
    db_path = tmp_path / "erpguard.db"
    backup_dir = tmp_path / "backups"

    connection = sqlite3.connect(db_path)
    connection.execute("create table release_probe(id integer primary key, value text)")
    connection.execute("insert into release_probe(value) values ('ok')")
    connection.commit()
    connection.close()

    script = ROOT / "scripts" / "backup_release_db.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db-path",
            str(db_path),
            "--backup-dir",
            str(backup_dir),
            "--json",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    body = json.loads(result.stdout)
    backup_path = Path(body["backup_path"])
    assert body["status"] == "backed_up"
    assert backup_path.exists()
    assert backup_path.parent == backup_dir
    assert backup_path.name.startswith("erpguard-")
    assert "password" not in result.stdout.lower()
    assert "secret" not in result.stdout.lower()


def test_backup_release_db_missing_file_fails_with_clear_message(tmp_path):
    script = ROOT / "scripts" / "backup_release_db.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--db-path",
            str(tmp_path / "missing.db"),
            "--backup-dir",
            str(tmp_path / "backups"),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "database file not found" in result.stderr.lower()


def test_update_release_candidate_script_documents_safe_update_flow():
    script = ROOT / "scripts" / "update_release_candidate.sh"
    assert script.exists()

    text = script.read_text(encoding="utf-8")
    assert "git pull origin main" in text
    assert 'pip install -e ".[dev]"' in text
    assert "systemctl restart erpguard" in text
    assert "scripts/ops_check.py --base-url" in text
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=true" not in text
    assert "ALLOW_R3_R4_REAL_WRITES=true" not in text
