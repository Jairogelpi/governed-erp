from __future__ import annotations

import os

from erpguard.product.google_calendar_fixture_client import (
    FixtureReadResult,
    GoogleCalendarFixtureClient,
)

# Real reads are disabled by default. Set USE_REAL_GOOGLE_CALENDAR=true to enable.
# When enabled, this client requires a valid OAuth access token via the auth profile vault.
# The token is never logged, stored plaintext, or returned in API responses.
_REAL_READ_ENABLED = os.environ.get("USE_REAL_GOOGLE_CALENDAR", "false").lower() == "true"


class GoogleCalendarReadOnlyClient:
    """
    Read-only Google Calendar client. Dispatches to fixture or real path based on flag.
    NEVER creates, updates, or deletes calendar events.
    """

    CONNECTOR_ID = "google_calendar_readonly"
    ALLOWED_SCOPE = "https://www.googleapis.com/auth/calendar.readonly"

    def __init__(self, access_token: str | None = None):
        self._access_token = access_token
        self._fixture = GoogleCalendarFixtureClient()

    def read_calendars(self) -> FixtureReadResult:
        if _REAL_READ_ENABLED and self._access_token:
            return self._real_read_calendars()
        return self._fixture.read_calendars()

    def read_upcoming_events(self, max_results: int = 10) -> FixtureReadResult:
        if _REAL_READ_ENABLED and self._access_token:
            return self._real_read_upcoming_events(max_results=max_results)
        return self._fixture.read_upcoming_events(max_results=max_results)

    def _real_read_calendars(self) -> FixtureReadResult:
        # Real path: requires google-api-python-client installed and a valid token.
        # Guarded behind USE_REAL_GOOGLE_CALENDAR=true.
        try:
            from googleapiclient.discovery import build  # type: ignore
            from google.oauth2.credentials import Credentials  # type: ignore
        except ImportError:
            return self._fixture.read_calendars()

        creds = Credentials(token=self._access_token, scopes=[self.ALLOWED_SCOPE])
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        response = service.calendarList().list(maxResults=50).execute()
        items = response.get("items", [])
        return FixtureReadResult(
            fixture_mode=False,
            operation="read_calendars",
            items=items,
            total_count=len(items),
            read_only=True,
            write_attempted=False,
        )

    def _real_read_upcoming_events(self, max_results: int = 10) -> FixtureReadResult:
        try:
            from datetime import datetime, timezone
            from googleapiclient.discovery import build  # type: ignore
            from google.oauth2.credentials import Credentials  # type: ignore
        except ImportError:
            return self._fixture.read_upcoming_events(max_results=max_results)

        creds = Credentials(token=self._access_token, scopes=[self.ALLOWED_SCOPE])
        service = build("calendar", "v3", credentials=creds, cache_discovery=False)
        now_iso = datetime.now(timezone.utc).isoformat()
        response = (
            service.events()
            .list(
                calendarId="primary",
                timeMin=now_iso,
                maxResults=max_results,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        items = response.get("items", [])
        return FixtureReadResult(
            fixture_mode=False,
            operation="read_upcoming_events",
            items=items,
            total_count=len(items),
            read_only=True,
            write_attempted=False,
        )
