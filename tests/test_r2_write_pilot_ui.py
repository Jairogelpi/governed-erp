from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


def test_demo_dashboard_has_r2_section():
    resp = client.get("/demo")
    assert resp.status_code == 200
    html = resp.text
    assert "R2 Controlled Write Pilot" in html
    assert "res.partner.write" in html


def test_demo_dashboard_r2_buttons_present():
    resp = client.get("/demo")
    html = resp.text
    assert "r2CreateRequest" in html
    assert "r2CheckPolicy" in html
    assert "r2Execute" in html
    assert "r2GetRun" in html
    assert "r2GetEvidence" in html
    assert "r2History" in html


def test_demo_dashboard_r2_output_elements():
    resp = client.get("/demo")
    html = resp.text
    assert "r2-request-output" in html
    assert "r2-policy-output" in html
    assert "r2-run-output" in html
    assert "r2-evidence-output" in html
    assert "r2-history-output" in html


def test_demo_dashboard_r2_safety_text():
    resp = client.get("/demo")
    html = resp.text
    assert "ALLOW_R2_REAL_WRITE_PILOT=false" in html
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=false" in html
    assert "ALLOW_R3_R4_REAL_WRITES=false" in html
    assert "staging" in html
    assert "demo" in html


def test_demo_dashboard_r2_allowed_fields_mentioned():
    resp = client.get("/demo")
    html = resp.text
    assert "comment" in html
    assert "website" in html


def test_demo_dashboard_r2_blocked_actions_mentioned():
    resp = client.get("/demo")
    html = resp.text
    assert "sale.order.action_confirm" in html or "action_confirm" in html
    assert "account.move.action_post" in html or "action_post" in html


def test_demo_dashboard_r2_api_paths_in_js():
    resp = client.get("/demo")
    html = resp.text
    assert "/r2-write-pilot/request" in html
    assert "/r2-write-pilot/requests/" in html
    assert "policy-check" in html
    assert "execute" in html
    assert "/evidence" in html


def test_demo_dashboard_still_has_sprint10a():
    resp = client.get("/demo")
    html = resp.text
    assert "End-to-End Operator Flow" in html


def test_demo_dashboard_still_has_sprint9():
    resp = client.get("/demo")
    html = resp.text
    assert "Production Safety" in html
