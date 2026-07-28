from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConnectorSignal:
    signal_code: str
    title: str
    value: str
    severity: str
    connector_id: str
    fixture_mode: bool

    def model_dump(self) -> dict:
        return {
            "signal_code": self.signal_code,
            "title": self.title,
            "value": self.value,
            "severity": self.severity,
            "connector_id": self.connector_id,
            "fixture_mode": self.fixture_mode,
        }


class ConnectorSignalGenerator:
    """
    Generates safe business signals from redacted connector read data.
    Never includes PII, tokens, emails, or raw event content.
    Only aggregated counts and boolean indicators.
    """

    def generate_from_events(
        self, events: list[dict], fixture_mode: bool, connector_id: str = "google_calendar_readonly"
    ) -> list[ConnectorSignal]:
        signals: list[ConnectorSignal] = []

        total = len(events)
        confirmed = sum(1 for e in events if e.get("status") == "confirmed")
        tentative = sum(1 for e in events if e.get("status") == "tentative")

        signals.append(ConnectorSignal(
            signal_code="upcoming_events_count",
            title="Upcoming Events Count",
            value=str(total),
            severity="info",
            connector_id=connector_id,
            fixture_mode=fixture_mode,
        ))

        signals.append(ConnectorSignal(
            signal_code="calendar_active",
            title="Calendar Active",
            value="true" if total > 0 else "false",
            severity="info",
            connector_id=connector_id,
            fixture_mode=fixture_mode,
        ))

        signals.append(ConnectorSignal(
            signal_code="confirmed_events",
            title="Confirmed Events",
            value=str(confirmed),
            severity="info",
            connector_id=connector_id,
            fixture_mode=fixture_mode,
        ))

        if tentative > 0:
            signals.append(ConnectorSignal(
                signal_code="tentative_events",
                title="Tentative Events",
                value=str(tentative),
                severity="low",
                connector_id=connector_id,
                fixture_mode=fixture_mode,
            ))

        signals.append(ConnectorSignal(
            signal_code="fixture_mode_active",
            title="Fixture Mode Active",
            value="true" if fixture_mode else "false",
            severity="info",
            connector_id=connector_id,
            fixture_mode=fixture_mode,
        ))

        return signals

    def generate_from_calendars(
        self, calendars: list[dict], fixture_mode: bool, connector_id: str = "google_calendar_readonly"
    ) -> list[ConnectorSignal]:
        return [
            ConnectorSignal(
                signal_code="calendars_accessible",
                title="Calendars Accessible",
                value=str(len(calendars)),
                severity="info",
                connector_id=connector_id,
                fixture_mode=fixture_mode,
            ),
            ConnectorSignal(
                signal_code="fixture_mode_active",
                title="Fixture Mode Active",
                value="true" if fixture_mode else "false",
                severity="info",
                connector_id=connector_id,
                fixture_mode=fixture_mode,
            ),
        ]
