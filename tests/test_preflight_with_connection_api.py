from fastapi.testclient import TestClient

import apps.api.routes.preflight as preflight_route
from apps.api.main import app
from erpguard.adapters.fake import FakeERPAdapter


def create_connection(client: TestClient, erp_type: str = "fake", api_key: str = "secret") -> dict:
    response = client.post(
        "/v1/connections",
        json={
            "name": f"{erp_type.title()} Test",
            "erp_type": erp_type,
            "config": {
                "url": "https://example.odoo.com",
                "database": "example-db",
                "username": "user@example.com",
                "api_key": api_key,
            },
        },
    )
    assert response.status_code == 200
    return response.json()


def make_connection_payload(connection_id: str, target_id: str = "so_valid", policy_id: str = "formula_guard") -> dict:
    return {
        "connection_id": connection_id,
        "actor": {
            "type": "user",
            "id": "user_1",
            "display_name": "Test User",
        },
        "action": {
            "canonical_action": "confirm_sales_order",
            "canonical_object": "SalesOrder",
            "native": {
                "model": "sale.order",
                "method": "action_confirm",
                "record_id": target_id,
            },
        },
        "options": {"simulate": True, "allow_write": False},
        "policy_id": policy_id,
    }


def test_preflight_with_fake_connection_valid_order_requires_approval():
    client = TestClient(app)
    connection = create_connection(client, erp_type="fake")

    response = client.post("/v1/preflight", json=make_connection_payload(connection["id"], "so_valid"))

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "require_approval"
    assert body["risk_level"] == "R3"
    assert body["approval_required"] is True
    assert body["target_id"] == "so_valid"


def test_preflight_with_fake_connection_invalid_order_returns_block():
    client = TestClient(app)
    connection = create_connection(client, erp_type="fake")

    response = client.post("/v1/preflight", json=make_connection_payload(connection["id"], "so_formula_mismatch"))

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "block"
    assert body["issues"][0]["code"] == "formula_ml_per_unit_mismatch"


def test_preflight_missing_connection_id_returns_controlled_404():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_connection_payload("conn_missing", "so_valid"))

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "connection_not_found"


def test_preflight_with_odoo_connection_uses_factory_without_exposing_api_key(monkeypatch):
    client = TestClient(app)
    connection = create_connection(client, erp_type="odoo", api_key="super-secret")
    resolved = {}

    def fake_create_adapter_from_connection(stored_connection):
        resolved["erp_type"] = stored_connection.erp_type
        resolved["config_json"] = stored_connection.config_json
        return FakeERPAdapter()

    monkeypatch.setattr(preflight_route, "create_adapter_from_connection", fake_create_adapter_from_connection)

    response = client.post("/v1/preflight", json=make_connection_payload(connection["id"], "40"))

    assert response.status_code == 200
    assert response.json()["decision"] == "block"
    assert resolved["erp_type"] == "odoo"
    assert "super-secret" in resolved["config_json"]
    assert "super-secret" not in response.text


def test_old_erp_type_fake_preflight_request_still_works():
    client = TestClient(app)

    response = client.post(
        "/v1/preflight",
        json={
            "erp_type": "fake",
            "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
            "action": {"canonical_action": "confirm_sales_order", "target_id": "so_valid"},
            "policy_id": "formula_guard",
        },
    )

    assert response.status_code == 200
    assert response.json()["decision"] == "require_approval"


def test_invalid_connection_config_returns_controlled_400():
    client = TestClient(app)
    response = client.post(
        "/v1/connections",
        json={"name": "Bad Odoo", "erp_type": "odoo", "config": {"api_key": "bad-secret"}},
    )
    connection = response.json()

    preflight_response = client.post("/v1/preflight", json=make_connection_payload(connection["id"], "40"))

    assert preflight_response.status_code == 400
    assert preflight_response.json()["error"]["code"] == "adapter_configuration_error"
    assert "bad-secret" not in preflight_response.text


def test_health_endpoint_still_works_with_connection_preflight():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
