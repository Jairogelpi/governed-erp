from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)
BASE = "/v1/operator-console/erp-adapters"


def test_api_lists_adapters():
    response = client.get(BASE)
    assert response.status_code == 200
    body = response.json()
    assert any(item["adapter_id"] == "fake_erp" for item in body["adapters"])
    assert body["is_advisory_only"] is True
    assert body["will_execute"] is False
    assert body["can_execute"] is False


def test_api_lists_capabilities():
    response = client.get(f"{BASE}/odoo_placeholder/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["adapter_found"] is True
    assert any(item["operation_type"] == "read_object" for item in body["capabilities"])


def test_api_checks_capability():
    response = client.post(
        f"{BASE}/capability-check",
        json={
            "adapter_id": "odoo_placeholder",
            "operation_type": "read_object",
            "object_type": "partner",
            "requested_fields": ["name", "email"],
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["supported"] is True
    assert body["safety_tier"] == "read_only"
    assert body["is_advisory_only"] is True
    assert body["will_execute"] is False
    assert body["can_execute"] is False


def test_unknown_adapter_returns_stable_response():
    response = client.get(f"{BASE}/missing_adapter/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert body["adapter_found"] is False
    assert body["blocking_reasons"] == ["adapter_not_found"]
