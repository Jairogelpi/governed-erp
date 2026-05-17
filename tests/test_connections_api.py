from fastapi.testclient import TestClient

from apps.api.main import app


def make_payload(erp_type: str = "odoo", api_key: str = "secret") -> dict:
    return {
        "name": "Odoo Test",
        "erp_type": erp_type,
        "config": {
            "url": "https://example.odoo.com",
            "database": "example-db",
            "username": "user@example.com",
            "api_key": api_key,
        },
    }


def test_create_fake_connection_redacts_api_key():
    client = TestClient(app)

    response = client.post("/v1/connections", json=make_payload(erp_type="fake"))

    assert response.status_code == 200
    body = response.json()
    assert body["id"].startswith("conn_")
    assert body["erp_type"] == "fake"
    assert body["config"]["api_key"] == "***REDACTED***"
    assert "secret" not in response.text


def test_create_odoo_connection_redacts_api_key():
    client = TestClient(app)

    response = client.post("/v1/connections", json=make_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["erp_type"] == "odoo"
    assert body["config"]["url"] == "https://example.odoo.com"
    assert body["config"]["api_key"] == "***REDACTED***"
    assert "secret" not in response.text


def test_get_connection_redacts_api_key():
    client = TestClient(app)
    created = client.post("/v1/connections", json=make_payload(api_key="top-secret")).json()

    response = client.get(f"/v1/connections/{created['id']}")

    assert response.status_code == 200
    assert response.json()["config"]["api_key"] == "***REDACTED***"
    assert "top-secret" not in response.text


def test_list_connections_redacts_api_key():
    client = TestClient(app)
    client.post("/v1/connections", json=make_payload(api_key="list-secret"))

    response = client.get("/v1/connections")

    assert response.status_code == 200
    assert all(item["config"].get("api_key") != "list-secret" for item in response.json())
    assert "list-secret" not in response.text


def test_invalid_erp_type_returns_controlled_400():
    client = TestClient(app)

    response = client.post("/v1/connections", json=make_payload(erp_type="unknown"))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "unsupported_erp_type"


def test_health_endpoint_still_works_with_connections_route_registered():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
