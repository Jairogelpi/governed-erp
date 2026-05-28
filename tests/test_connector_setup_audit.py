from __future__ import annotations

from fastapi.testclient import TestClient

from apps.api.main import app


client = TestClient(app)
BASE = "/v1/operator-console/connectors"


def test_audit_records_setup_session_created():
    created = client.post(
        f"{BASE}/setup-session",
        json={
            "connector_name": "Audit ERP",
            "erp_url": "https://audit.example.com",
            "environment_type": "staging",
            "submitted_by": "operator_audit",
        },
    ).json()

    response = client.get(f"{BASE}/setup-session-audit")

    assert response.status_code == 200
    body = response.json()
    matching = [event for event in body["events"] if event["session_id"] == created["session_id"]]
    assert [event["event_type"] for event in matching] == [
        "setup_session_requested",
        "setup_session_created",
    ]
    assert matching[-1]["status"] == "awaiting_credentials"
    assert matching[-1]["submitted_by"] == "operator_audit"
    assert body["event_count"] >= 2


def test_audit_records_blocked_session_without_raw_secret_values():
    response = client.post(
        f"{BASE}/setup-session",
        json={
            "connector_name": "Blocked Secret ERP",
            "erp_url": "https://blocked.example.com",
            "environment_type": "production",
            "submitted_by": "operator_audit",
            "token": "raw_token_never_persist",
        },
    )
    created = response.json()

    audit_response = client.get(f"{BASE}/setup-session-audit")

    assert audit_response.status_code == 200
    assert "raw_token_never_persist" not in audit_response.text
    matching = [event for event in audit_response.json()["events"] if event["session_id"] == created["session_id"]]
    assert matching[-1]["event_type"] == "setup_session_blocked"
    assert "raw_credentials_not_allowed_in_sprint_54" in matching[-1]["detail"]["blocking_reasons"]
    assert matching[-1]["detail"]["credentials_stored"] is False
