"""Tests for Sprint 58 - Generated Capabilities UI on /demo."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_ui_exposes_generated_capabilities_section():
    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Generated Capabilities" in response.content
    assert b"Sprint 58" in response.content
    assert b"gcDiscoveryPlanId" in response.content
    assert b"gcCreatedBy" in response.content
    assert b"gcCapabilitySetId" in response.content
    assert b"gcGenerate" in response.content
    assert b"gcGet" in response.content
    assert b"gcList" in response.content
    assert b"gcAudit" in response.content


def test_ui_generated_capabilities_banner_states_generation_only_boundary():
    response = client.get("/demo")

    assert response.status_code == 200
    assert b"advisory capabilities from the safe discovery plan only" in response.content
    assert b"does not connect to the ERP, login, inspect schemas" in response.content
