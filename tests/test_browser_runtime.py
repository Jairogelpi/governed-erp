from __future__ import annotations

import socket
import threading
import time
from contextlib import contextmanager

import httpx
import pytest
import uvicorn

from apps.api.main import app
from erpguard.runtime.browser_runtime import is_playwright_browser_available, run_fake_erp_formula_skill_ui


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


def test_browser_runtime_allow_path_returns_allow_and_captures_evidence():
    _require_browser_or_skip()

    with run_test_server() as base_url:
        result = run_fake_erp_formula_skill_ui(base_url, "SO-VALID")

    assert result.decision == "allow"
    assert result.status == "success"
    assert result.no_llm_used is True
    assert result.token_economics["repeated_execution_token_cost"] == 0
    assert any("/fake-erp/sales/orders" in url for url in result.visited_urls)
    assert any("order-search" in selector for selector in result.selectors_used)
    assert [step.step_id for step in result.steps] == [
        "browser_open_orders",
        "browser_search_order",
        "browser_open_order",
        "browser_open_formula",
        "browser_review_formula",
        "browser_extract_formula",
        "formula_guard",
        "produce_result",
    ]


def test_browser_runtime_block_path_returns_block():
    _require_browser_or_skip()

    with run_test_server() as base_url:
        result = run_fake_erp_formula_skill_ui(base_url, "SO-FORMULA-MISMATCH")

    assert result.decision == "block"
    assert result.status == "success"
    assert result.output["policy_id"] == "formula_guard"
    assert result.output["policy_version"] == "0.1.0"
    assert result.token_economics["estimated_tokens_saved"] == 2000


def test_browser_runtime_missing_order_returns_controlled_failure():
    _require_browser_or_skip()

    with run_test_server() as base_url:
        result = run_fake_erp_formula_skill_ui(base_url, "SO-MISSING")

    assert result.status == "failed"
    assert result.decision == "block"
    assert result.error_text is not None