from __future__ import annotations

from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field


def _iso(dt: datetime) -> str:
    return dt.isoformat()


def _fixture_calendars() -> list[dict]:
    return [
        {
            "id": "fixture_primary_calendar",
            "summary": "Primary Calendar (fixture)",
            "primary": True,
            "accessRole": "owner",
        },
        {
            "id": "fixture_team_calendar",
            "summary": "Team Calendar (fixture)",
            "primary": False,
            "accessRole": "reader",
        },
    ]


def _fixture_events(max_results: int = 10) -> list[dict]:
    now = datetime.now(timezone.utc)
    events: list[dict] = [
        {
            "id": "fixture_event_001",
            "summary": "Weekly Team Standup",
            "start": {"dateTime": _iso(now + timedelta(days=1, hours=9))},
            "end": {"dateTime": _iso(now + timedelta(days=1, hours=9, minutes=30))},
            "status": "confirmed",
            "organizer": {"email": "[redacted]", "displayName": "Team Lead"},
            "attendees": [
                {"email": "[redacted]", "responseStatus": "accepted"},
                {"email": "[redacted]", "responseStatus": "tentative"},
            ],
            "hangoutLink": "[redacted]",
            "htmlLink": "[redacted]",
            "description": "[redacted]",
        },
        {
            "id": "fixture_event_002",
            "summary": "Product Review",
            "start": {"dateTime": _iso(now + timedelta(days=2, hours=14))},
            "end": {"dateTime": _iso(now + timedelta(days=2, hours=15))},
            "status": "confirmed",
            "organizer": {"email": "[redacted]"},
            "attendees": [
                {"email": "[redacted]", "responseStatus": "accepted"},
            ],
            "hangoutLink": "[redacted]",
            "htmlLink": "[redacted]",
            "description": "[redacted]",
        },
        {
            "id": "fixture_event_003",
            "summary": "1:1 with Manager",
            "start": {"dateTime": _iso(now + timedelta(days=3, hours=10))},
            "end": {"dateTime": _iso(now + timedelta(days=3, hours=10, minutes=45))},
            "status": "confirmed",
            "organizer": {"email": "[redacted]"},
            "attendees": [],
            "hangoutLink": "[redacted]",
            "htmlLink": "[redacted]",
            "description": "[redacted]",
        },
        {
            "id": "fixture_event_004",
            "summary": "Sprint Planning",
            "start": {"dateTime": _iso(now + timedelta(days=4, hours=9))},
            "end": {"dateTime": _iso(now + timedelta(days=4, hours=11))},
            "status": "confirmed",
            "organizer": {"email": "[redacted]"},
            "attendees": [
                {"email": "[redacted]", "responseStatus": "accepted"},
                {"email": "[redacted]", "responseStatus": "accepted"},
                {"email": "[redacted]", "responseStatus": "needsAction"},
            ],
            "hangoutLink": "[redacted]",
            "htmlLink": "[redacted]",
            "description": "[redacted]",
        },
        {
            "id": "fixture_event_005",
            "summary": "Customer Demo",
            "start": {"dateTime": _iso(now + timedelta(days=5, hours=15))},
            "end": {"dateTime": _iso(now + timedelta(days=5, hours=16))},
            "status": "tentative",
            "organizer": {"email": "[redacted]"},
            "attendees": [],
            "hangoutLink": "[redacted]",
            "htmlLink": "[redacted]",
            "description": "[redacted]",
        },
    ]
    return events[:max_results]


@dataclass
class FixtureReadResult:
    fixture_mode: bool = True
    connector_id: str = "google_calendar_readonly"
    operation: str = ""
    items: list[dict] = field(default_factory=list)
    total_count: int = 0
    read_only: bool = True
    write_attempted: bool = False


class GoogleCalendarFixtureClient:
    """Returns deterministic fixture data. No network calls, no credentials required."""

    CONNECTOR_ID = "google_calendar_readonly"

    def read_calendars(self) -> FixtureReadResult:
        items = _fixture_calendars()
        return FixtureReadResult(
            operation="read_calendars",
            items=items,
            total_count=len(items),
        )

    def read_upcoming_events(self, max_results: int = 10) -> FixtureReadResult:
        items = _fixture_events(max_results=max_results)
        return FixtureReadResult(
            operation="read_upcoming_events",
            items=items,
            total_count=len(items),
        )
