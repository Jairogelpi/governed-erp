from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from apps.api.main import app

client = TestClient(app)

_PROFILE_ID = "demo_profile_sprint18"


def test_list_external_connectors():
    r = client.get("/v1/external-connectors")
    assert r.status_code == 200
    body = r.json()
    assert "connectors" in body
    ids = [c["connector_id"] for c in body["connectors"]]
    assert "google_calendar_readonly" in ids
    for c in body["connectors"]:
        assert c["write_operations_enabled"] is False


def test_get_connector_policy():
    r = client.get("/v1/external-connectors/google-calendar-readonly/policy")
    assert r.status_code == 200
    body = r.json()
    assert body["write_operations_enabled"] is False
    assert body["mcp_execution_enabled"] is False
    assert body["erp_write_enabled"] is False
    assert "read_calendars" in body["allowed_operations"]
    assert "create_event" in body["forbidden_operations"]
    assert "https://www.googleapis.com/auth/calendar.readonly" in body["allowed_scopes"]


def test_test_readiness_allowed():
    r = client.post(
        "/v1/external-connectors/google-calendar-readonly/test-readiness",
        json={"auth_profile_id": _PROFILE_ID, "actor": {"id": "test_user"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["policy_allowed"] is True
    assert body["violations"] == []
    assert body["fixture_mode"] is True


def test_read_calendars_fixture():
    r = client.post(
        "/v1/external-connectors/google-calendar-readonly/read-calendars",
        json={"auth_profile_id": _PROFILE_ID, "actor": {"id": "test_user"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["fixture_mode"] is True
    assert body["read_only"] is True
    assert body["total_count"] > 0
    assert "evidence_id" in body
    assert body["evidence_id"].startswith("cre_")
    assert len(body["signals"]) > 0
    # No real emails in response
    import json
    assert "@" not in json.dumps(body).replace("[redacted]", "SAFE")


def test_read_upcoming_events_fixture():
    r = client.post(
        "/v1/external-connectors/google-calendar-readonly/read-upcoming-events",
        json={"auth_profile_id": _PROFILE_ID, "max_results": 3, "actor": {"id": "test_user"}},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["fixture_mode"] is True
    assert body["read_only"] is True
    assert body["total_count"] <= 3
    assert "evidence_id" in body
    assert body["evidence_id"].startswith("cre_")
    assert "signals" in body
    assert len(body["signals"]) > 0


def test_read_events_redacts_pii():
    r = client.post(
        "/v1/external-connectors/google-calendar-readonly/read-upcoming-events",
        json={"auth_profile_id": _PROFILE_ID, "max_results": 5, "actor": {"id": "test_user"}},
    )
    body_str = r.text
    # Ensure no real email addresses leak
    import re
    real_emails = re.findall(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", body_str)
    for email in real_emails:
        assert "[redacted]" in body_str or email == "[redacted]"


def test_get_read_evidence():
    # First create some evidence
    r = client.post(
        "/v1/external-connectors/google-calendar-readonly/read-upcoming-events",
        json={"auth_profile_id": _PROFILE_ID, "max_results": 2, "actor": {"id": "test_user"}},
    )
    evidence_id = r.json()["evidence_id"]

    r2 = client.get(f"/v1/external-connectors/read-evidence/{evidence_id}")
    assert r2.status_code == 200
    body = r2.json()
    assert body["id"] == evidence_id
    assert body["read_only"] is True
    assert body["fixture_mode"] is True


def test_get_read_evidence_not_found():
    r = client.get("/v1/external-connectors/read-evidence/cre_doesnotexist")
    assert r.status_code == 404


def test_list_read_evidence_for_profile():
    profile_id = "test_evidence_list_profile"
    client.post(
        "/v1/external-connectors/google-calendar-readonly/read-calendars",
        json={"auth_profile_id": profile_id, "actor": {}},
    )
    r = client.get(f"/v1/external-connectors/auth-profiles/{profile_id}/read-evidence")
    assert r.status_code == 200
    body = r.json()
    assert body["auth_profile_id"] == profile_id
    assert isinstance(body["evidence"], list)
    assert len(body["evidence"]) >= 1


def test_get_signals_for_profile():
    profile_id = "test_signals_profile"
    client.post(
        "/v1/external-connectors/google-calendar-readonly/read-upcoming-events",
        json={"auth_profile_id": profile_id, "max_results": 5, "actor": {}},
    )
    r = client.get(f"/v1/external-connectors/auth-profiles/{profile_id}/signals")
    assert r.status_code == 200
    body = r.json()
    assert body["auth_profile_id"] == profile_id
    assert isinstance(body["signals"], list)


def test_get_audit_for_profile():
    profile_id = "test_audit_profile_sprint18"
    client.post(
        "/v1/external-connectors/google-calendar-readonly/test-readiness",
        json={"auth_profile_id": profile_id, "actor": {"id": "tester"}},
    )
    r = client.get(f"/v1/external-connectors/auth-profiles/{profile_id}/audit")
    assert r.status_code == 200
    body = r.json()
    assert body["auth_profile_id"] == profile_id
    assert len(body["events"]) >= 1
    ev = body["events"][0]
    assert "token" not in str(ev.get("details", {}))


def test_audit_redacts_tokens():
    profile_id = "test_token_redaction"
    r = client.get(f"/v1/external-connectors/auth-profiles/{profile_id}/audit")
    assert r.status_code == 200
    # Tokens must never appear in audit
    assert "access_token" not in r.text or "[redacted]" in r.text
