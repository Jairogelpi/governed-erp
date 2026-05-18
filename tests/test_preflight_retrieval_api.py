from fastapi.testclient import TestClient

from apps.api.main import app


def create_fake_connection(client: TestClient, api_key: str = "secret") -> str:
    response = client.post(
        "/v1/connections",
        json={"name": "Fake Test", "erp_type": "fake", "config": {"api_key": api_key}},
    )
    assert response.status_code == 200
    return response.json()["id"]


def run_preflight(client: TestClient, connection_id: str, target_id: str) -> dict:
    response = client.post(
        "/v1/preflight",
        json={
            "connection_id": connection_id,
            "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
            "action": {"canonical_action": "confirm_sales_order", "target_id": target_id},
            "policy_id": "formula_guard",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_get_preflight_by_id_returns_same_decision():
    client = TestClient(app)
    connection_id = create_fake_connection(client)
    created = run_preflight(client, connection_id, "so_valid")

    response = client.get(f"/v1/preflight/{created['preflight_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["preflight_id"] == created["preflight_id"]
    assert body["decision"] == created["decision"]
    assert body["risk_level"] == created["risk_level"]
    assert body["actor"]["id"] == "user_1"
    assert body["canonical_action"] == "confirm_sales_order"
    assert body["canonical_object"] == "SalesOrder"
    assert body["created_at"]


def test_get_preflight_invalid_formula_includes_invariant_results():
    client = TestClient(app)
    connection_id = create_fake_connection(client)
    created = run_preflight(client, connection_id, "so_formula_mismatch")

    response = client.get(f"/v1/preflight/{created['preflight_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "block"
    assert body["invariant_results"][0]["invariant_id"] == "formula_ml_per_unit_mismatch"
    assert body["invariant_results"][0]["severity"] == "blocking"


def test_missing_preflight_id_returns_404():
    client = TestClient(app)

    response = client.get("/v1/preflight/pf_missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "preflight_not_found"


def test_preflight_retrieval_does_not_expose_api_key_or_connection_config():
    client = TestClient(app)
    connection_id = create_fake_connection(client, api_key="retrieval-secret")
    created = run_preflight(client, connection_id, "so_formula_mismatch")

    response = client.get(f"/v1/preflight/{created['preflight_id']}")

    assert response.status_code == 200
    assert "retrieval-secret" not in response.text
    assert "config_json" not in response.text


def test_health_endpoint_still_works_with_preflight_retrieval():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
