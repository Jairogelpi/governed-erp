"""API tests for Sprint 80 - visual browser session shell."""

from fastapi.testclient import TestClient

from apps.api.main import app
from erpguard.db.session import init_db


def test_api_create_get_list_revoke_and_audit_visual_browser_session():
    init_db()
    client = TestClient(app)

    created = client.post(
        "/v1/operator-console/visual-browser/sessions",
        json={
            "created_by": "operator_1",
            "target_url": "https://my-erp.example.com",
            "intended_erp_hint": "odoo",
            "workspace_mode": "observe_only",
        },
    )

    assert created.status_code == 200
    payload = created.json()
    assert payload["visual_session_id"].startswith("vbs_")
    assert payload["credential_capture_allowed"] is False
    assert payload["browser_launched"] is False

    retrieved = client.get(
        f"/v1/operator-console/visual-browser/session/{payload['visual_session_id']}"
    )
    listed = client.get("/v1/operator-console/visual-browser/sessions")
    revoked = client.post(
        f"/v1/operator-console/visual-browser/session/{payload['visual_session_id']}/revoke",
        json={"actor": "operator_1"},
    )
    audit = client.get("/v1/operator-console/visual-browser/audit")

    assert retrieved.status_code == 200
    assert retrieved.json()["visual_session_id"] == payload["visual_session_id"]
    assert listed.status_code == 200
    assert any(
        item["visual_session_id"] == payload["visual_session_id"]
        for item in listed.json()["sessions"]
    )
    assert revoked.status_code == 200
    assert revoked.json()["status"] == "revoked"
    assert audit.status_code == 200
    event_types = [event["event_type"] for event in audit.json()["events"]]
    assert "visual_browser_session_created" in event_types
    assert "visual_browser_session_retrieved" in event_types
    assert "visual_browser_session_revoked" in event_types


def test_api_blocks_forbidden_credential_capture_attempt():
    init_db()
    client = TestClient(app)

    response = client.post(
        "/v1/operator-console/visual-browser/sessions",
        json={
            "created_by": "operator_1",
            "credential_capture_allowed": True,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "blocked"
    assert payload["blocking_reasons"] == ["credential_capture_forbidden"]
    assert payload["credential_capture_allowed"] is False
