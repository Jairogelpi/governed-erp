"""UI tests for Sprint 79 - Odoo read-only demo flow."""

from fastapi.testclient import TestClient

from apps.api.main import app


def test_ui_exposes_odoo_read_only_demo_flow_section():
    client = TestClient(app)

    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Odoo Read-Only Demo Flow" in response.content
    assert b"Sprint 79 runs an operator-facing read-only Odoo demo flow" in response.content
    assert b"odooDemoActivationId" in response.content
    assert b"odooDemoObjectTypes" in response.content
    assert b"odooDemoRun" in response.content
    assert b"odooDemoAudit" in response.content
