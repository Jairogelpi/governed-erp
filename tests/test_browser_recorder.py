from __future__ import annotations

import builtins
import socket
import threading
import time
from contextlib import contextmanager

import httpx
import pytest
import uvicorn
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.recorder.browser_recorder import record_fake_erp_formula_review_flow
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


def test_browser_recorder_creates_finished_recording_and_ordered_events(monkeypatch):
    _require_browser_or_skip()

    original_import = builtins.__import__

    def guarded_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith(("openai", "anthropic", "langchain", "llm")):
            raise AssertionError(f"Unexpected LLM import: {name}")
        return original_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", guarded_import)

    with run_test_server() as base_url:
        result = record_fake_erp_formula_review_flow(
            base_url=base_url,
            order_reference="SO-FORMULA-MISMATCH",
            actor={"type": "user", "id": "user_1", "display_name": "Test User"},
        )

    assert result.status == "finished"
    assert result.no_llm_used is True
    assert result.order_reference == "SO-FORMULA-MISMATCH"
    assert result.event_count == 5
    assert result.visited_urls
    assert result.selectors_used == [
        "[data-testid='order-search']",
        "[data-testid='open-order-SO-FORMULA-MISMATCH']",
        "[data-testid='formula-tab']",
        "[data-testid='review-formula']",
    ]
    assert [step.step_id for step in result.steps] == [
        "browser_open_orders",
        "browser_search_order",
        "browser_open_order",
        "browser_open_formula",
        "browser_review_formula",
    ]

    init_db_client = TestClient(app)
    response = init_db_client.get(f"/v1/recordings/{result.recording_id}")
    assert response.status_code == 200
    recording_body = response.json()
    assert recording_body["status"] == "finished"
    assert [event["event_index"] for event in recording_body["events"]] == [1, 2, 3, 4, 5]
    assert recording_body["event_count"] == 5
    assert recording_body["events"][1]["selector"] == "[data-testid='order-search']"


def test_health_endpoint_still_works_after_recorder_routes():
    client = TestClient(app)

    response = client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}