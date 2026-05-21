from __future__ import annotations

import pytest

from erpguard.product.external_connector_policy import ExternalConnectorPolicy


@pytest.fixture
def policy():
    return ExternalConnectorPolicy()


def test_allowed_operations_pass(policy):
    for op in ("test_readiness", "read_calendars", "read_upcoming_events"):
        result = policy.check("google_calendar_readonly", op)
        assert result.allowed is True
        assert result.violations == []


def test_forbidden_operations_blocked(policy):
    for op in ("create_event", "update_event", "delete_event", "send_email", "mcp_execute", "erp_write"):
        result = policy.check("google_calendar_readonly", op)
        assert result.allowed is False
        assert len(result.violations) > 0


def test_unknown_operation_blocked(policy):
    result = policy.check("google_calendar_readonly", "some_unknown_op")
    assert result.allowed is False


def test_allowed_scopes_returned(policy):
    result = policy.check("google_calendar_readonly", "read_calendars")
    assert "https://www.googleapis.com/auth/calendar.readonly" in result.allowed_scopes


def test_connector_policy_dict(policy):
    p = policy.get_connector_policy("google_calendar_readonly")
    assert p["write_operations_enabled"] is False
    assert p["mcp_execution_enabled"] is False
    assert p["arbitrary_http_enabled"] is False
    assert p["erp_write_enabled"] is False
    assert "read_calendars" in p["allowed_operations"]
    assert "create_event" in p["forbidden_operations"]


def test_list_connectors(policy):
    connectors = policy.list_connectors()
    assert len(connectors) >= 1
    ids = [c["connector_id"] for c in connectors]
    assert "google_calendar_readonly" in ids
    for c in connectors:
        assert c["write_operations_enabled"] is False
