from fastapi.testclient import TestClient

from apps.api.main import app


def create_connection_and_preflight(client: TestClient, target_id: str = "so_formula_mismatch") -> dict:
    connection = client.post(
        "/v1/connections",
        json={"name": "Fake Test", "erp_type": "fake", "config": {"api_key": "audit-secret"}},
    ).json()
    response = client.post(
        "/v1/preflight",
        json={
            "connection_id": connection["id"],
            "actor": {"type": "user", "id": "user_1", "display_name": "Test User"},
            "action": {"canonical_action": "confirm_sales_order", "target_id": target_id},
            "policy_id": "formula_guard",
        },
    )
    assert response.status_code == 200
    return response.json()


def test_audit_endpoint_returns_preflight_summary_invariants_and_events():
    client = TestClient(app)
    created = create_connection_and_preflight(client)

    response = client.get(f"/v1/audit/{created['preflight_id']}")

    assert response.status_code == 200
    body = response.json()
    assert body["case_id"] == created["preflight_id"]
    assert body["preflight_case"]["decision"] == "block"
    assert body["invariant_results"][0]["invariant_id"] == "formula_ml_per_unit_mismatch"
    assert [event["event_type"] for event in body["audit_events"]] == [
        "PREFLIGHT_CREATED",
        "PREFLIGHT_DECIDED",
    ]
    assert body["execution"] is None


def test_audit_events_are_sorted_by_created_at():
    client = TestClient(app)
    created = create_connection_and_preflight(client)

    response = client.get(f"/v1/audit/{created['preflight_id']}")

    events = response.json()["audit_events"]
    timestamps = [event["created_at"] for event in events]
    assert timestamps == sorted(timestamps)


def test_audit_response_does_not_expose_api_key_or_connection_config():
    client = TestClient(app)
    created = create_connection_and_preflight(client)

    response = client.get(f"/v1/audit/{created['preflight_id']}")

    assert response.status_code == 200
    assert "audit-secret" not in response.text
    assert "config_json" not in response.text


def test_missing_audit_case_returns_404():
    client = TestClient(app)

    response = client.get("/v1/audit/pf_missing")

    assert response.status_code == 404
    assert response.json()["error"]["code"] == "audit_case_not_found"


def test_health_endpoint_still_works_with_audit_route_registered():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
