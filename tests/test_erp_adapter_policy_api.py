from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)


def test_api_policy_check_works():
    response = client.post(
        "/v1/operator-console/erp-adapters/policy-check",
        json={
            "adapter_id": "odoo_placeholder",
            "operation_type": "preview_write",
            "object_type": "sale_order",
            "requested_fields": ["state"],
            "actor": "operator_1",
            "has_confirmed_token": False,
            "has_credentials": False,
            "phase": "block_c_contract_only",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["eligible"] is True
    assert body["can_preview"] is True
    assert body["can_execute"] is False
    assert body["is_advisory_only"] is True
    assert body["will_execute"] is False
