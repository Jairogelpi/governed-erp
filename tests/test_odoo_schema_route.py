"""Schema-driven capability declaration: `GET /v1/connectors/odoo/connections/
{connection_id}/schema/{model}` -- lets the UI list real, currently-existing
fields on any model instead of the user typing one blind (PR #59's own plan
flagged this as deferred). Read-only, backed by `fields_get`, same technique
`test_phase16_7_pricing_scenario_draft.py` uses to inject a fake transport at
the HTTP layer.
"""

from __future__ import annotations

from uuid import uuid4

from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.application.connectors.service import ConnectorApplicationService
from erpguard.config import settings
from erpguard.db.session import init_db

from test_phase14_skill_compiler import _identity


class _FakeReadTransport:
    def __init__(self, fields: dict) -> None:
        self._fields = fields

    def fields_get(self, model: str, attributes=None) -> dict:
        return self._fields


def _setup(monkeypatch) -> tuple[TestClient, dict]:
    monkeypatch.setattr(settings, "auth_secret", "skill-auth")
    monkeypatch.setattr(settings, "local_secret_key", Fernet.generate_key().decode())
    init_db()
    tenant_id = f"schema-tenant-{uuid4().hex}"
    headers = _identity(tenant_id)
    return TestClient(app), headers


def _odoo_connection(client: TestClient, headers: dict) -> str:
    resp = client.post(
        "/v1/connections",
        headers=headers,
        json={
            "name": f"odoo-conn-{uuid4().hex[:8]}",
            "connector_type": "odoo",
            "endpoint": "https://odoo.example.test",
            "auth_type": "api_key",
            "secret": "fake-odoo-secret",
            "metadata": {"database": "test_db", "username": "test_user", "environment": "staging"},
        },
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def test_returns_real_fields_from_transport(monkeypatch):
    client, headers = _setup(monkeypatch)
    connection_id = _odoo_connection(client, headers)
    transport = _FakeReadTransport(
        {
            "loyalty_discount_pct": {"type": "float", "string": "Loyalty discount %", "readonly": False},
            "id": {"type": "integer", "string": "ID", "readonly": True},
        }
    )
    monkeypatch.setattr(
        ConnectorApplicationService, "_odoo_transport_factory", lambda self, connection: (lambda context: transport)
    )

    resp = client.get(f"/v1/connectors/odoo/connections/{connection_id}/schema/res.partner", headers=headers)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["model"] == "res.partner"
    names = {field["name"] for field in body["fields"]}
    assert names == {"loyalty_discount_pct", "id"}
    id_field = next(field for field in body["fields"] if field["name"] == "id")
    assert id_field["readonly"] is True
    assert id_field["type"] == "integer"


def test_rejects_malformed_model_identifier(monkeypatch):
    client, headers = _setup(monkeypatch)
    connection_id = _odoo_connection(client, headers)

    resp = client.get(f"/v1/connectors/odoo/connections/{connection_id}/schema/DROP TABLE", headers=headers)

    assert resp.status_code == 400


def test_unknown_connection_returns_404(monkeypatch):
    client, headers = _setup(monkeypatch)

    resp = client.get("/v1/connectors/odoo/connections/conn_does_not_exist/schema/res.partner", headers=headers)

    assert resp.status_code == 404
