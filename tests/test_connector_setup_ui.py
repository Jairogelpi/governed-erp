from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_ui_exposes_connector_autopilot_setup_section():
    html = client.get("/demo").text

    assert "Connector Autopilot - Setup Session" in html
    assert "Sprint 54 creates a connector setup session only." in html
    assert "It does not store credentials, call ERP URLs" in html


def test_connector_setup_fields_and_buttons_present():
    html = client.get("/demo").text

    for marker in (
        "connectorSetupName",
        "connectorSetupUrl",
        "connectorSetupEnv",
        "connectorSetupSubmittedBy",
        "connectorSetupSessionId",
        "connectorSetupOutput",
        "Create connector setup session",
        "Get setup session",
        "List setup sessions",
        "Setup session audit",
        "/v1/operator-console/connectors/setup-session",
        "/v1/operator-console/connectors/setup-sessions",
        "/v1/operator-console/connectors/setup-session-audit",
    ):
        assert marker in html
