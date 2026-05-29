"""Tests for Sprint 56 — ERP Fingerprinting Plan UI on /demo."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_ui_exposes_fingerprinting_plan_card():
    response = client.get("/demo")
    assert response.status_code == 200
    assert b"ERP Fingerprinting Plan" in response.content
    assert b"Sprint 56" in response.content
    assert b"fpCreatePlan" in response.content
    assert b"fpGetPlan" in response.content
    assert b"fpListPlans" in response.content
    assert b"fpAudit" in response.content


def test_ui_fingerprinting_has_manual_hint_select():
    response = client.get("/demo")
    assert response.status_code == 200
    assert b"fpManualHint" in response.content
    assert b"odoo" in response.content


def test_ui_fingerprinting_has_session_and_credential_inputs():
    response = client.get("/demo")
    assert response.status_code == 200
    assert b"fpSessionId" in response.content
    assert b"fpCredRef" in response.content


def test_ui_fingerprinting_safety_banner():
    response = client.get("/demo")
    assert response.status_code == 200
    assert (
        b"does not call the ERP URL" in response.content
        or b"fingerprinting plan only" in response.content
    )
