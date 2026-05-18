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
            response = httpx.get(f"{base_url}/health", timeout=0.5)
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


def create_skill(base_url: str) -> str:
    response = httpx.post(
        f"{base_url}/v1/skills",
        json={
            "name": "UI Formula Guard Skill",
            "description": "Deterministic browser runtime test skill.",
            "runtime_type": "deterministic_browser",
            "llm_required_for_repeated_runs": False,
            "skill_package": {
                "skill_id": "ui_formula_guard_skill",
                "inputs": {"order_reference": "string"},
                "guards": ["formula_guard"],
                "workflow": [],
            },
        },
        timeout=5,
    )
    assert response.status_code == 200
    return response.json()["skill_id"]


def test_skill_run_ui_allow_path_returns_zero_token_repeat_cost():
    _require_browser_or_skip()

    with run_test_server() as base_url:
        skill_id = create_skill(base_url)
        response = httpx.post(
            f"{base_url}/v1/skills/{skill_id}/run-ui",
            json={"inputs": {"order_reference": "SO-VALID"}, "runtime": {"base_url": base_url}},
            timeout=60,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert body["decision"] == "allow"
    assert body["token_economics"]["repeated_execution_token_cost"] == 0
    assert body["visited_urls"]
    assert body["selectors_used"]


def test_skill_run_ui_block_path_returns_block():
    _require_browser_or_skip()

    with run_test_server() as base_url:
        skill_id = create_skill(base_url)
        response = httpx.post(
            f"{base_url}/v1/skills/{skill_id}/run-ui",
            json={"inputs": {"order_reference": "SO-FORMULA-MISMATCH"}, "runtime": {"base_url": base_url}},
            timeout=60,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "block"
    assert body["output"]["policy_id"] == "formula_guard"
    assert body["steps"]


def test_skill_run_ui_missing_order_returns_controlled_failure():
    _require_browser_or_skip()

    with run_test_server() as base_url:
        skill_id = create_skill(base_url)
        response = httpx.post(
            f"{base_url}/v1/skills/{skill_id}/run-ui",
            json={"inputs": {"order_reference": "SO-MISSING"}, "runtime": {"base_url": base_url}},
            timeout=60,
        )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "failed"
    assert body["decision"] == "block"


def test_health_endpoint_still_works():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}