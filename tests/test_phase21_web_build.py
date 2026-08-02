"""Spec 94 -- the frontend build is a CI gate, same as the Docker image
build: a broken `web/` build must fail CI. Skipped when `web/node_modules`
is absent (the default `quality` job does not run `npm ci`); the dedicated
`frontend` CI job does, so it always exercises this for real."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

WEB_DIR = Path(__file__).resolve().parents[1] / "web"

pytestmark = pytest.mark.skipif(
    not (WEB_DIR / "node_modules").is_dir(),
    reason="web/node_modules absent -- run `npm ci` in web/ first (see the `frontend` CI job)",
)


def _npm_command() -> list[str]:
    return ["npm.cmd"] if sys.platform == "win32" else ["npm"]


def test_frontend_build_succeeds_and_produces_expected_assets() -> None:
    result = subprocess.run(
        [*_npm_command(), "run", "build"],
        cwd=WEB_DIR,
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert result.returncode == 0, f"npm run build failed:\n{result.stdout}\n{result.stderr}"

    dist_dir = WEB_DIR / "dist"
    assert (dist_dir / "index.html").is_file()

    manifest_path = dist_dir / ".vite" / "manifest.json"
    assert manifest_path.is_file()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert "index.html" in manifest
    assert (dist_dir / manifest["index.html"]["file"]).is_file()


def test_static_app_is_served_alongside_the_api_once_built() -> None:
    # Import after the build above so `apps.api.app_factory.WEB_DIST_DIR`
    # is present on disk when the app is constructed.
    from fastapi.testclient import TestClient

    from apps.api.app_factory import create_public_app

    client = TestClient(create_public_app(include_internal=False, serve_frontend=True))

    root = client.get("/")
    assert root.status_code == 200
    assert "<div id=\"root\">" in root.text

    deep_link = client.get("/canary")
    assert deep_link.status_code == 200
    assert "<div id=\"root\">" in deep_link.text

    assert client.get("/v1/health").status_code == 200
    assert client.get("/assets/does-not-exist.js").status_code == 404
