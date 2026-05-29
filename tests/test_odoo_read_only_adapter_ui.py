"""Tests for Sprint 74 - Odoo read-only adapter shell UI."""

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_ui_exposes_odoo_read_only_adapter_shell_section():
    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Odoo Read-Only Adapter Shell" in response.content
    assert b"Sprint 74" in response.content
    assert b"odooRoActivationId" in response.content
    assert b"odooRoAdapterSessionId" in response.content
    assert b"odooRoCreatedBy" in response.content
    assert b"odooRoCreate" in response.content
    assert b"odooRoGet" in response.content
    assert b"odooRoList" in response.content
    assert b"odooRoAudit" in response.content


def test_ui_odoo_adapter_banner_states_shell_only_boundary():
    response = client.get("/demo")

    assert response.status_code == 200
    assert b"Odoo read-only adapter shell only" in response.content
    assert b"does not connect to Odoo, perform HTTP/XML-RPC/JSON-RPC" in response.content
