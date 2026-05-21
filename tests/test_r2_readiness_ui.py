from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db

client = TestClient(app)


@pytest.fixture(autouse=True)
def _init():
    init_db()


def test_dashboard_has_sprint11_section():
    html = client.get("/demo").text
    assert "R2 Pilot Evidence Review" in html
    assert "Rollback Rehearsal" in html
    assert "Production Readiness" in html


def test_dashboard_sprint11_buttons():
    html = client.get("/demo").text
    assert "r2rEvidenceReview" in html
    assert "r2rRollbackRehearsal" in html
    assert "r2rExecutionReport" in html
    assert "r2rPromotionGate" in html


def test_dashboard_sprint11_outputs():
    html = client.get("/demo").text
    assert "r2r-review-output" in html
    assert "r2r-rehearsal-output" in html
    assert "r2r-report-output" in html
    assert "r2r-gate-output" in html


def test_dashboard_sprint11_api_paths():
    html = client.get("/demo").text
    assert "evidence-review" in html
    assert "rollback-rehearsal" in html
    assert "execution-report" in html
    assert "promotion-gate" in html


def test_dashboard_sprint11_safety_text():
    html = client.get("/demo").text
    assert "ALLOW_GENERIC_REAL_ODOO_WRITES=false" in html
    assert "ALLOW_R3_R4_REAL_WRITES=false" in html
    assert "Real rollback never auto-executed" in html or "real_rollback_executed" in html


def test_dashboard_still_has_sprint10b():
    html = client.get("/demo").text
    assert "R2 Controlled Write Pilot" in html


def test_dashboard_still_has_sprint10a():
    html = client.get("/demo").text
    assert "End-to-End Operator Flow" in html
