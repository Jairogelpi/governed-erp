from __future__ import annotations

import pytest

from erpguard.product.connector_signal_generator import ConnectorSignalGenerator


@pytest.fixture
def gen():
    return ConnectorSignalGenerator()


def _events(n: int = 3) -> list[dict]:
    return [{"id": f"e{i}", "status": "confirmed"} for i in range(n)]


def test_generate_from_events_returns_signals(gen):
    signals = gen.generate_from_events(_events(3), fixture_mode=True)
    codes = [s.signal_code for s in signals]
    assert "upcoming_events_count" in codes
    assert "calendar_active" in codes
    assert "confirmed_events" in codes
    assert "fixture_mode_active" in codes


def test_events_count_signal_value(gen):
    signals = gen.generate_from_events(_events(4), fixture_mode=True)
    count_signal = next(s for s in signals if s.signal_code == "upcoming_events_count")
    assert count_signal.value == "4"


def test_calendar_active_true_when_events(gen):
    signals = gen.generate_from_events(_events(2), fixture_mode=True)
    active = next(s for s in signals if s.signal_code == "calendar_active")
    assert active.value == "true"


def test_calendar_active_false_when_empty(gen):
    signals = gen.generate_from_events([], fixture_mode=True)
    active = next(s for s in signals if s.signal_code == "calendar_active")
    assert active.value == "false"


def test_tentative_signal_added_when_present(gen):
    events = [
        {"id": "e1", "status": "confirmed"},
        {"id": "e2", "status": "tentative"},
    ]
    signals = gen.generate_from_events(events, fixture_mode=True)
    codes = [s.signal_code for s in signals]
    assert "tentative_events" in codes


def test_tentative_signal_absent_when_none(gen):
    signals = gen.generate_from_events(_events(2), fixture_mode=True)
    codes = [s.signal_code for s in signals]
    assert "tentative_events" not in codes


def test_fixture_mode_signal_reflects_flag(gen):
    signals_fixture = gen.generate_from_events([], fixture_mode=True)
    signals_real = gen.generate_from_events([], fixture_mode=False)
    fm_f = next(s for s in signals_fixture if s.signal_code == "fixture_mode_active")
    fm_r = next(s for s in signals_real if s.signal_code == "fixture_mode_active")
    assert fm_f.value == "true"
    assert fm_r.value == "false"


def test_signals_contain_no_pii(gen):
    import json
    events = [{"id": "e1", "status": "confirmed", "organizer": {"email": "test@example.com"}}]
    signals = gen.generate_from_events(events, fixture_mode=True)
    output = json.dumps([s.model_dump() for s in signals])
    assert "test@example.com" not in output


def test_generate_from_calendars(gen):
    cals = [{"id": "c1"}, {"id": "c2"}]
    signals = gen.generate_from_calendars(cals, fixture_mode=True)
    codes = [s.signal_code for s in signals]
    assert "calendars_accessible" in codes
    count_sig = next(s for s in signals if s.signal_code == "calendars_accessible")
    assert count_sig.value == "2"
