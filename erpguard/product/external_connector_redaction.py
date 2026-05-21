from __future__ import annotations

import copy
from dataclasses import dataclass, field


_REDACT_SENTINEL = "[redacted]"

# Top-level event fields that must always be redacted
_TOP_LEVEL_REDACT = {
    "hangoutLink",
    "htmlLink",
    "description",
}

# Nested paths: (parent_key, child_key)
_NESTED_REDACT = {
    ("organizer", "email"),
    ("creator", "email"),
    ("conferenceData", None),  # redact entire object
}


@dataclass
class RedactionResult:
    redacted_event: dict
    redacted_fields: list[str] = field(default_factory=list)


def redact_calendar_event(event: dict) -> RedactionResult:
    result = copy.deepcopy(event)
    redacted_fields: list[str] = []

    for key in _TOP_LEVEL_REDACT:
        if key in result:
            result[key] = _REDACT_SENTINEL
            redacted_fields.append(key)

    for parent_key, child_key in _NESTED_REDACT:
        if parent_key in result:
            if child_key is None:
                result[parent_key] = _REDACT_SENTINEL
                redacted_fields.append(parent_key)
            elif isinstance(result[parent_key], dict) and child_key in result[parent_key]:
                result[parent_key][child_key] = _REDACT_SENTINEL
                redacted_fields.append(f"{parent_key}.{child_key}")

    if "attendees" in result and isinstance(result["attendees"], list):
        for i, attendee in enumerate(result["attendees"]):
            if isinstance(attendee, dict) and "email" in attendee:
                result["attendees"][i]["email"] = _REDACT_SENTINEL
                redacted_fields.append(f"attendees[{i}].email")
            if isinstance(attendee, dict) and "displayName" in attendee:
                result["attendees"][i]["displayName"] = _REDACT_SENTINEL
                redacted_fields.append(f"attendees[{i}].displayName")

    return RedactionResult(redacted_event=result, redacted_fields=redacted_fields)


def redact_calendar_events(events: list[dict]) -> tuple[list[dict], int]:
    redacted_events = []
    total_redacted = 0
    for event in events:
        r = redact_calendar_event(event)
        redacted_events.append(r.redacted_event)
        total_redacted += len(r.redacted_fields)
    return redacted_events, total_redacted


def redact_calendar_item(calendar: dict) -> dict:
    result = copy.deepcopy(calendar)
    for key in ("description", "timeZone"):
        if key in result:
            result.pop(key, None)
    return result
