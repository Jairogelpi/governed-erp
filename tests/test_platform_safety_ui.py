from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


def test_demo_dashboard_contains_sprint9_section():
    resp = client.get("/demo")
    assert resp.status_code == 200
    html = resp.text
    assert "Production Safety" in html
    assert "Tenant Controls" in html


def test_demo_dashboard_sprint9_buttons_present():
    resp = client.get("/demo")
    html = resp.text
    assert "psaCreateTenant" in html
    assert "psaGetSafetySummary" in html
    assert "psaActivateKillSwitch" in html
    assert "psaDeactivateKillSwitch" in html
    assert "psaGenerateAuditExport" in html
    assert "psaEvaluatePolicy" in html
    assert "psaGetRuntimeSafety" in html


def test_demo_dashboard_sprint9_output_elements_present():
    resp = client.get("/demo")
    html = resp.text
    assert "psa-tenant-output" in html
    assert "psa-summary-output" in html
    assert "psa-kill-switch-output" in html
    assert "psa-audit-export-output" in html
    assert "psa-policy-output" in html
    assert "psa-runtime-output" in html


def test_demo_dashboard_sprint9_safety_invariants_mentioned():
    resp = client.get("/demo")
    html = resp.text
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=false" in html
    assert "ALLOW_R3_R4_REAL_WRITES=false" in html


def test_demo_dashboard_sprint9_kill_switch_names_mentioned():
    resp = client.get("/demo")
    html = resp.text
    assert "global_kill_switch" in html
    assert "runtime_execution_kill_switch" in html
    assert "write_pilot_kill_switch" in html


def test_demo_dashboard_sprint9_js_handlers_present():
    resp = client.get("/demo")
    html = resp.text
    assert "psaCreateTenant" in html
    assert "psaActivateKillSwitch" in html
    assert "/v1/platform/tenants" in html
    assert "/v1/platform/policy/evaluate" in html
    assert "/v1/platform/runtime-safety" in html


def test_demo_dashboard_still_has_sprint8_section():
    resp = client.get("/demo")
    html = resp.text
    assert "First Real Write Pilot" in html
    assert "mail.message.create" in html


def test_demo_dashboard_still_has_sprint7_section():
    resp = client.get("/demo")
    html = resp.text
    assert "Write Capability Readiness" in html
    assert "Risk Certification" in html
