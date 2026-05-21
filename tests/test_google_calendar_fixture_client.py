from __future__ import annotations

import pytest

from erpguard.product.google_calendar_fixture_client import GoogleCalendarFixtureClient


@pytest.fixture
def client():
    return GoogleCalendarFixtureClient()


def test_read_calendars_returns_fixture(client):
    result = client.read_calendars()
    assert result.fixture_mode is True
    assert result.read_only is True
    assert result.write_attempted is False
    assert result.total_count > 0
    assert len(result.items) == result.total_count


def test_read_calendars_no_pii(client):
    import json
    result = client.read_calendars()
    output = json.dumps(result.items)
    assert "@" not in output or "[redacted]" in output


def test_read_upcoming_events_returns_fixture(client):
    result = client.read_upcoming_events(max_results=3)
    assert result.fixture_mode is True
    assert result.read_only is True
    assert result.write_attempted is False
    assert result.total_count <= 3
    assert len(result.items) <= 3


def test_read_upcoming_events_respects_max(client):
    result = client.read_upcoming_events(max_results=2)
    assert result.total_count <= 2


def test_fixture_events_already_redacted(client):
    import json
    result = client.read_upcoming_events()
    output = json.dumps(result.items)
    assert "meet.google.com" not in output or "[redacted]" in output


def test_no_write_operation_exists(client):
    assert not hasattr(client, "create_event")
    assert not hasattr(client, "update_event")
    assert not hasattr(client, "delete_event")
    assert not hasattr(client, "send_email")
