from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


def test_dashboard_has_release_section():
    html = client.get("/demo").text
    assert "Release Candidate" in html
    assert "v0.12.0-rc1" in html
    assert "Operator Demo Pack" in html


def test_dashboard_release_buttons_present():
    html = client.get("/demo").text
    assert "rcHealth" in html
    assert "rcReadiness" in html
    assert "rcDemoSeed" in html
    assert "rcSmoke" in html
    assert "rcSafetyBoundaries" in html


def test_dashboard_release_output_elements():
    html = client.get("/demo").text
    assert "rc-health-output" in html
    assert "rc-readiness-output" in html
    assert "rc-seed-output" in html
    assert "rc-smoke-output" in html
    assert "rc-safety-output" in html


def test_dashboard_release_api_paths():
    html = client.get("/demo").text
    assert "/v1/release/health" in html
    assert "/v1/release/readiness-report" in html
    assert "/v1/release/demo-seed" in html
    assert "/v1/release/operator-smoke" in html
    assert "/v1/release/safety-boundaries" in html


def test_dashboard_release_safety_text():
    html = client.get("/demo").text
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=false" in html
    assert "ALLOW_R3_R4_REAL_WRITES=false" in html
    assert "can_execute_real_writes=false" in html


def test_dashboard_release_sprint_count():
    html = client.get("/demo").text
    assert "13 sprints" in html or "Sprint 12" in html


def test_dashboard_still_has_sprint11():
    html = client.get("/demo").text
    assert "R2 Pilot Evidence Review" in html


def test_dashboard_still_has_sprint10b():
    html = client.get("/demo").text
    assert "R2 Controlled Write Pilot" in html
