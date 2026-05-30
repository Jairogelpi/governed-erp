"""UI tests for Sprint 75 - Odoo connection test demo section."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_odoo_connection_test_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Odoo Read-Only Connection Test" in response.content
    assert b"Sprint 75 performs only a controlled Odoo connection/auth test" in response.content
    assert b"odooCtAdapterSessionId" in response.content
    assert b"odooCtAllowNetworkTest" in response.content
    assert b"odooCtRun" in response.content
    assert b"odooCtAudit" in response.content


def test_ui_states_no_business_data_or_writes_boundary():
    client = TestClient(app)

    response = client.get("/demo")

    assert b"It does not read business data" in response.content
    assert b"write to Odoo" in response.content
    assert b"expose credentials" in response.content
