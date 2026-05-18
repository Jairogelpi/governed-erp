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


def test_preflight_valid_fake_order_requires_approval_for_confirm():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_payload("so_valid"))

    assert response.status_code == 200
    body = response.json()
    assert body["preflight_id"].startswith("pf_")
    assert body["decision"] == "require_approval"
    assert body["risk_level"] == "R3"
    assert body["approval_required"] is True
    assert body["blocking_issues"] == []
    assert body["predicted_impact"]["simulation_status"] == "not_implemented"
    assert body["actor"]["id"] == "user_1"
    assert body["canonical_action"] == "confirm_sales_order"
    assert body["canonical_object"] == "SalesOrder"
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
    assert body["approval_required"] is False
    assert body["blocking_issues"][0]["code"] == "formula_ml_per_unit_mismatch"
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


def test_preflight_odoo_without_config_returns_controlled_error():
    client = TestClient(app)

    response = client.post("/v1/preflight", json=make_payload("so_valid", erp_type="odoo"))

    assert response.status_code == 400
    body = response.json()
    assert body["error"]["code"] == "adapter_configuration_error"
    assert "Odoo" in body["error"]["message"]


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


def test_preflight_rejects_allow_write_true():
    client = TestClient(app)
    payload = make_payload("so_valid")
    payload["options"]["allow_write"] = True

    response = client.post("/v1/preflight", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "writes_not_supported"


def test_preflight_rejects_canonical_object_mismatch():
    client = TestClient(app)
    payload = make_payload("so_valid")
    payload["action"]["canonical_object"] = "Invoice"

    response = client.post("/v1/preflight", json=payload)

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "canonical_object_mismatch"


def test_health_endpoint_still_works_with_preflight_route_registered():
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
