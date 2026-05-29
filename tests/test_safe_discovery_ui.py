"""Tests for Sprint 57 - Safe Discovery Plan UI on /demo."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_ui_exposes_safe_discovery_plan_section():
    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Safe Discovery Plan" in response.content
    assert b"Sprint 57" in response.content
    assert b"sdFingerprintPlanId" in response.content
    assert b"sdSelectedAdapterType" in response.content
    assert b"sdCreatePlan" in response.content
    assert b"sdGetPlan" in response.content
    assert b"sdListPlans" in response.content
    assert b"sdAudit" in response.content


def test_ui_safe_discovery_banner_states_plan_only_boundary():
    response = client.get("/demo")

    assert response.status_code == 200
    assert b"read-only surface model only" in response.content
    assert b"does not connect, login, inspect schemas" in response.content
