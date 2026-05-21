from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


def test_demo_dashboard_contains_sprint10a_section():
    resp = client.get("/demo")
    assert resp.status_code == 200
    html = resp.text
    assert "ERP Agent OS" in html
    assert "End-to-End Operator Flow" in html


def test_demo_dashboard_sprint10a_buttons_present():
    resp = client.get("/demo")
    html = resp.text
    assert "ofCreateSession" in html
    assert "ofSelectConnection" in html
    assert "ofRunNext" in html
    assert "ofRunSafeReadonly" in html
    assert "ofTimeline" in html
    assert "ofSummary" in html


def test_demo_dashboard_sprint10a_output_elements():
    resp = client.get("/demo")
    html = resp.text
    assert "of-session-output" in html
    assert "of-run-output" in html
    assert "of-timeline-output" in html
    assert "of-summary-output" in html


def test_demo_dashboard_sprint10a_safety_text():
    resp = client.get("/demo")
    html = resp.text
    assert "can_execute_real_writes=false" in html
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=false" in html


def test_demo_dashboard_sprint10a_api_paths_in_js():
    resp = client.get("/demo")
    html = resp.text
    assert "/v1/product/operator-sessions" in html
    assert "run-next" in html
    assert "run-safe-readonly-path" in html
    assert "timeline" in html
    assert "summary" in html


def test_demo_dashboard_sprint10a_js_handlers():
    resp = client.get("/demo")
    html = resp.text
    assert "ofCreateSession" in html
    assert "ofRunNext" in html
    assert "ofRunSafeReadonly" in html


def test_demo_dashboard_still_has_sprint9():
    resp = client.get("/demo")
    html = resp.text
    assert "Production Safety" in html
    assert "Tenant Controls" in html


def test_demo_dashboard_still_has_sprint8():
    resp = client.get("/demo")
    html = resp.text
    assert "First Real Write Pilot" in html


def test_demo_dashboard_still_has_sprint7():
    resp = client.get("/demo")
    html = resp.text
    assert "Write Capability Readiness" in html
