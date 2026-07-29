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


def _require_browser_or_skip():
    if not is_playwright_browser_available():
        pytest.skip("Playwright browser binaries are unavailable in this environment.")


def test_demo_endpoint_records_compiles_and_runs_skill():
    _require_browser_or_skip()

    with run_test_server() as base_url:
        demo_response = httpx.post(
            f"{base_url}/v1/recordings/demo-fake-erp-formula-flow",
            json={
                "base_url": base_url,
                "order_reference": "SO-FORMULA-MISMATCH",
                "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
            },
            timeout=120,
        )
        assert demo_response.status_code == 200
        demo_body = demo_response.json()
        assert demo_body["status"] == "finished"
        assert demo_body["event_count"] == 5
        assert demo_body["no_llm_used"] is True
        assert any("/fake-erp/sales/orders" in url for url in demo_body["visited_urls"])

        compile_response = httpx.post(
            f"{base_url}/v1/recordings/{demo_body['recording_id']}/compile-skill",
            json={
                "name": "Recorded Fake ERP Formula Review",
                "description": "Compiled from a demonstrated Fake ERP formula review flow.",
                "runtime_type": "deterministic_browser",
            },
            timeout=60,
        )
        assert compile_response.status_code == 200
        compile_body = compile_response.json()
        assert compile_body["skill_package"]["compiled_from_recording_id"] == demo_body["recording_id"]

        allow_run = httpx.post(
            f"{base_url}/v1/skills/{compile_body['skill_id']}/run",
            json={"inputs": {"order_reference": "SO-VALID"}},
            timeout=60,
        )
        assert allow_run.status_code == 200
        assert allow_run.json()["decision"] == "allow"

        block_run = httpx.post(
            f"{base_url}/v1/skills/{compile_body['skill_id']}/run",
            json={"inputs": {"order_reference": "SO-FORMULA-MISMATCH"}},
            timeout=60,
        )
        assert block_run.status_code == 200
        assert block_run.json()["decision"] == "block"


def test_health_endpoint_still_works():
    client = TestClient(app)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}