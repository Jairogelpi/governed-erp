from fastapi.testclient import TestClient

from apps.api.main import app


def make_payload(target_id: str = "so_valid", erp_type: str = "fake", policy_id: str = "formula_guard") -> dict:
    return {
        "erp_type": erp_type,
        "actor": {
            "type": "user",
            "id": "user_1",
            "display_name": "Test User",
        },
        "action": {
            "canonical_action": "validate_formula",
            "target_id": target_id,
        },
        "policy_id": policy_id,
    }


def test_preflight_valid_fake_order_returns_allow():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_payload("so_valid"))

    assert response.status_code == 200
    body = response.json()
    assert body["preflight_id"].startswith("pf_")
    assert body["decision"] == "allow"
    assert body["risk_level"] == "R0"
    assert body["actor"]["id"] == "user_1"
    assert body["canonical_action"] == "validate_formula"
    assert body["target_id"] == "so_valid"
    assert body["policy_id"] == "formula_guard"
    assert body["policy_version"] == "0.1.0"
    assert body["issues"] == []


def test_preflight_invalid_formula_order_returns_block():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_payload("so_formula_mismatch"))

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "block"
    assert body["risk_level"] == "R3"
    assert body["issues"][0]["code"] == "formula_ml_per_unit_mismatch"
    assert body["issues"][0]["line_id"] == "line_formula_mismatch"


def test_preflight_missing_target_fails_closed_with_block():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_payload("missing"))

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "block"
    assert body["issues"][0]["code"] == "preflight_target_load_failed"
    assert "missing" in body["summary"]


def test_preflight_unsupported_erp_type_returns_controlled_error():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_payload("so_valid", erp_type="odoo"))

    assert response.status_code == 501
    body = response.json()
    assert body["error"]["code"] == "adapter_not_implemented"
    assert "odoo" in body["error"]["message"]


def test_preflight_unknown_erp_type_returns_controlled_error():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_payload("so_valid", erp_type="unknown"))

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "unsupported_erp_type"


def test_preflight_unknown_policy_id_returns_controlled_block_response():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_payload("so_valid", policy_id="unknown_policy"))

    assert response.status_code == 200
    body = response.json()
    assert body["decision"] == "block"
    assert body["policy_id"] == "unknown_policy"
    assert body["issues"][0]["code"] == "preflight_target_load_failed"
    assert "unknown_policy" in body["summary"]


def test_health_endpoint_still_works_with_preflight_route_registered():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
