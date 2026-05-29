"""Tests for Sprint 59 - Read-Only Connector Activation UI."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_ui_exposes_read_only_connector_activation_section():
    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Read-Only Connector Activation" in response.content
    assert b"Sprint 59" in response.content
    assert b"roCapabilitySetId" in response.content
    assert b"roActivationRequestId" in response.content
    assert b"roActivationId" in response.content
    assert b"roRequestedBy" in response.content
    assert b"roApprovedBy" in response.content
    assert b"roMode" in response.content
    assert b"roCreateRequest" in response.content
    assert b"roApprove" in response.content
    assert b"roGet" in response.content
    assert b"roList" in response.content
    assert b"roAudit" in response.content


def test_ui_read_only_activation_banner_states_internal_artifact_boundary():
    response = client.get("/demo")

    assert response.status_code == 200
    assert b"internal read-only connector artifact" in response.content
    assert b"does not connect to the ERP, login, read ERP data" in response.content
