from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app


ROOT = Path(__file__).resolve().parents[1]


DEPLOYMENT_DOCS = [
    "docs/deployment/00_vps_deployment.md",
    "docs/deployment/01_systemd_service.md",
    "docs/deployment/02_operations_runbook.md",
    "docs/deployment/03_backup_and_restore.md",
    "docs/deployment/04_update_procedure.md",
    "docs/deployment/05_deployment_validation_report.md",
]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def test_deployment_docs_exist_and_cover_vps_operations_contract():
    for relative in DEPLOYMENT_DOCS:
        assert (ROOT / relative).exists(), relative

    combined = "\n".join(_read(relative) for relative in DEPLOYMENT_DOCS)
    for required in [
        "/opt/erpguard/app",
        "/opt/erpguard/.venv",
        "/var/lib/erpguard",
        "/etc/erpguard/erpguard.env",
        "systemctl restart erpguard",
        "journalctl -u erpguard",
        "python scripts/ops_check.py --base-url http://127.0.0.1:8000",
        "python scripts/backup_release_db.py",
        "validated_locally_with_vps_contract",
    ]:
        assert required in combined


def test_systemd_unit_uses_non_root_user_env_file_uvicorn_and_restart_policy():
    service = ROOT / "deploy" / "systemd" / "erpguard.service"
    assert service.exists()

    text = service.read_text(encoding="utf-8")
    assert "After=network.target" in text
    assert "User=erpguard" in text
    assert "Group=erpguard" in text
    assert "WorkingDirectory=/opt/erpguard/app" in text
    assert "EnvironmentFile=/etc/erpguard/erpguard.env" in text
    assert "apps.api.main:app" in text
    assert "--host 0.0.0.0" in text
    assert "--port 8000" in text
    assert "Restart=always" in text
    assert "WantedBy=multi-user.target" in text


def test_deployment_env_example_uses_persistent_paths_and_safe_defaults():
    env = ROOT / "deploy" / "env" / "erpguard.env.example"
    assert env.exists()

    text = env.read_text(encoding="utf-8")
    assert "ERPGUARD_ENV=release_candidate" in text
    assert "ERPGUARD_DATA_DIR=/var/lib/erpguard" in text
    assert "ERPGUARD_DB_URL=sqlite:////var/lib/erpguard/erpguard.db" in text
    assert "ERPGUARD_DATABASE_URL=sqlite:////var/lib/erpguard/erpguard.db" in text
    assert "ERPGUARD_HOST=0.0.0.0" in text
    assert "ERPGUARD_PORT=8000" in text
    assert "ALLOW_R1_REAL_WRITE_PILOT=false" in text
    assert "ALLOW_R2_REAL_WRITE_PILOT=false" in text
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=false" in text
    assert "ALLOW_R3_R4_REAL_WRITES=false" in text
    assert "password" not in text.lower()
    assert "api_key" not in text.lower()


def test_deployment_assets_do_not_enable_generic_or_high_risk_writes():
    asset_paths = [
        ROOT / "deploy" / "env" / "erpguard.env.example",
        ROOT / "deploy" / "systemd" / "erpguard.service",
        *[ROOT / relative for relative in DEPLOYMENT_DOCS],
    ]
    combined = "\n".join(path.read_text(encoding="utf-8").lower() for path in asset_paths)

    forbidden = [
        "allow_generic_real_odoo_writes=true",
        "allow_r3_r4_real_writes=true",
        "allow_r1_real_write_pilot=true",
        "allow_r2_real_write_pilot=true",
    ]
    for token in forbidden:
        assert token not in combined


def test_release_safety_boundaries_remain_unchanged_for_deployment_hardening():
    client = TestClient(app)
    body = client.get("/v1/release/safety-boundaries").json()
    boundaries = body["safety_boundaries"]

    assert boundaries["ALLOW_GENERIC_REAL_ODOO_WRITES"] is False
    assert boundaries["ALLOW_R3_R4_REAL_WRITES"] is False
    assert boundaries["ALLOW_R1_REAL_WRITE_PILOT"] is False
    assert boundaries["ALLOW_R2_REAL_WRITE_PILOT"] is False
    assert boundaries["can_execute_real_writes"] is False
