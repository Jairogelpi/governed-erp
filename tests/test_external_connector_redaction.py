from __future__ import annotations

from erpguard.product.external_connector_redaction import (
    redact_calendar_event,
    redact_calendar_events,
    redact_calendar_item,
)


def _sample_event():
    return {
        "id": "evt_001",
        "summary": "Team Meeting",
        "status": "confirmed",
        "hangoutLink": "https://meet.google.com/abc-def-ghi",
        "htmlLink": "https://calendar.google.com/event?eid=abc",
        "description": "Discuss Q2 roadmap with the team",
        "organizer": {"email": "boss@company.com", "displayName": "Boss"},
        "creator": {"email": "user@company.com"},
        "attendees": [
            {"email": "alice@company.com", "displayName": "Alice", "responseStatus": "accepted"},
            {"email": "bob@company.com", "displayName": "Bob", "responseStatus": "tentative"},
        ],
        "conferenceData": {"entryPoints": [{"uri": "https://meet.google.com/abc"}]},
    }


def test_hangout_link_redacted():
    event = _sample_event()
    result = redact_calendar_event(event)
    assert result.redacted_event["hangoutLink"] == "[redacted]"
    assert "hangoutLink" in result.redacted_fields


def test_html_link_redacted():
    event = _sample_event()
    result = redact_calendar_event(event)
    assert result.redacted_event["htmlLink"] == "[redacted]"


def test_description_redacted():
    event = _sample_event()
    result = redact_calendar_event(event)
    assert result.redacted_event["description"] == "[redacted]"


def test_organizer_email_redacted():
    event = _sample_event()
    result = redact_calendar_event(event)
    assert result.redacted_event["organizer"]["email"] == "[redacted]"


def test_creator_email_redacted():
    event = _sample_event()
    result = redact_calendar_event(event)
    assert result.redacted_event["creator"]["email"] == "[redacted]"


def test_attendee_emails_redacted():
    event = _sample_event()
    result = redact_calendar_event(event)
    for attendee in result.redacted_event["attendees"]:
        assert attendee["email"] == "[redacted]"
        assert attendee["displayName"] == "[redacted]"


def test_conference_data_redacted():
    event = _sample_event()
    result = redact_calendar_event(event)
    assert result.redacted_event["conferenceData"] == "[redacted]"


def test_summary_preserved():
    event = _sample_event()
    result = redact_calendar_event(event)
    assert result.redacted_event["summary"] == "Team Meeting"
    assert result.redacted_event["status"] == "confirmed"
    assert result.redacted_event["id"] == "evt_001"


def test_no_pii_in_output():
    event = _sample_event()
    result = redact_calendar_event(event)
    import json
    output_str = json.dumps(result.redacted_event)
    assert "boss@company.com" not in output_str
    assert "alice@company.com" not in output_str
    assert "bob@company.com" not in output_str
    assert "user@company.com" not in output_str
    assert "Discuss Q2" not in output_str
    assert "meet.google.com" not in output_str


def test_batch_redaction_counts():
    events = [_sample_event(), _sample_event()]
    safe_events, total_redacted = redact_calendar_events(events)
    assert len(safe_events) == 2
    assert total_redacted > 0


def test_calendar_item_redaction():
    cal = {"id": "cal_1", "summary": "My Calendar", "description": "Private notes", "timeZone": "Europe/Madrid"}
    safe = redact_calendar_item(cal)
    assert "description" not in safe
    assert "timeZone" not in safe
    assert safe["summary"] == "My Calendar"
