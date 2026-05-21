from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.main import app


ROOT = Path(__file__).resolve().parents[1]


def test_release_endpoints_and_demo_load_for_clean_install_contract():
    client = TestClient(app)

    assert client.get("/v1/release/health").status_code == 200
    assert client.get("/v1/release/readiness-report").status_code == 200
    assert client.post("/v1/release/demo-seed").status_code == 200
    assert client.post("/v1/release/operator-smoke").status_code == 200
    assert client.get("/v1/release/safety-boundaries").status_code == 200
    assert client.get("/demo").status_code == 200


def test_release_safety_boundaries_remain_locked_for_clean_install_contract():
    client = TestClient(app)
    health = client.get("/v1/release/health").json()
    boundaries = client.get("/v1/release/safety-boundaries").json()["safety_boundaries"]

    assert health["safety_boundaries_locked"] is True
    assert boundaries["ALLOW_GENERIC_REAL_ODOO_WRITES"] is False
    assert boundaries["ALLOW_R3_R4_REAL_WRITES"] is False
    assert boundaries["ALLOW_R1_REAL_WRITE_PILOT"] is False
    assert boundaries["ALLOW_R2_REAL_WRITE_PILOT"] is False
    assert boundaries["can_execute_real_writes"] is False


def test_check_release_install_script_has_help_and_imports_cleanly():
    script = ROOT / "scripts" / "check_release_install.py"
    assert script.exists()

    result = subprocess.run(
        [sys.executable, str(script), "--help"],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert "release install" in result.stdout.lower()


def test_start_scripts_reference_release_api_module_and_health_endpoint():
    bash_script = ROOT / "scripts" / "start_release_candidate.sh"
    ps_script = ROOT / "scripts" / "start_release_candidate.ps1"

    assert bash_script.exists()
    assert ps_script.exists()

    bash_text = bash_script.read_text(encoding="utf-8")
    ps_text = ps_script.read_text(encoding="utf-8")

    for text in (bash_text, ps_text):
        assert "uvicorn" in text
        assert "apps.api.main:app" in text
        assert "/v1/release/health" in text
