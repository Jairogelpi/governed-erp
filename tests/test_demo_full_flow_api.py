from __future__ import annotations

import socket
import threading
import time
from contextlib import contextmanager

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.runtime.browser_runtime import is_playwright_browser_available


@contextmanager
def run_test_server():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()

    config = uvicorn.Config(app, host=host, port=port, log_level="error")
    server = uvicorn.Server(config)
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    base_url = f"http://{host}:{port}"
    timeout = time.time() + 10
    while time.time() < timeout:
        try:
            response = httpx.get(f"{base_url}/v1/health", timeout=0.5)
            if response.status_code == 200:
                break
        except Exception:
            time.sleep(0.1)
    else:
        server.should_exit = True
        thread.join(timeout=5)
        raise RuntimeError("Test server did not start.")

    try:
        yield base_url
    finally:
        server.should_exit = True
        thread.join(timeout=5)


def test_demo_full_flow_returns_controlled_503_when_browser_runtime_unavailable(monkeypatch):
    monkeypatch.setattr("erpguard.recorder.browser_recorder.is_playwright_browser_available", lambda: False)

    with run_test_server() as base_url:
        response = httpx.post(
            f"{base_url}/v1/demo/full-record-to-skill-flow",
            json={
                "base_url": base_url,
                "record_order_reference": "SO-FORMULA-MISMATCH",
                "valid_order_reference": "SO-VALID",
                "invalid_order_reference": "SO-FORMULA-MISMATCH",
                "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
            },
            timeout=30,
        )

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "browser_runtime_unavailable",
            "message": "Playwright browser binaries are unavailable.",
        }
    }


def test_demo_full_flow_returns_success_when_browser_runtime_is_available():
    if not is_playwright_browser_available():
        pytest.skip("Playwright browser binaries are unavailable in this environment.")

    with run_test_server() as base_url:
        response = httpx.post(
            f"{base_url}/v1/demo/full-record-to-skill-flow",
            json={
                "base_url": base_url,
                "record_order_reference": "SO-FORMULA-MISMATCH",
                "valid_order_reference": "SO-VALID",
                "invalid_order_reference": "SO-FORMULA-MISMATCH",
                "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
            },
            timeout=120,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["recording"]["recording_id"]
    assert body["skill"]["skill_id"]
    assert body["runs"]["valid"]["decision"] == "allow"
    assert body["runs"]["invalid"]["decision"] == "block"
    assert body["runs"]["invalid"]["issues_count"] == 1
    assert body["token_economics"]["repeated_execution_token_cost"] == 0
    assert body["proof"]["erpguard_blocked_invalid_order"] is True


def test_health_endpoint_still_works():
    client = TestClient(app)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}