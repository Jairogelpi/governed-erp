from __future__ import annotations

from dataclasses import dataclass
from typing import Any


_KNOWN_ORDER_REFERENCES = (
    "SO-VALID",
    "SO-FORMULA-MISMATCH",
    "SO-CAPACITY-NO-FORMULA",
    "SO-EMPTY-LINES",
)


@dataclass(frozen=True)
class _EventView:
    event_type: str
    url: str | None
    page_title: str | None
    element_role: str | None
    element_text: str | None
    element_label: str | None
    selector: str | None
    input_value: str | None
    before_text_snapshot: str | None
    after_text_snapshot: str | None


def compile_recording_to_skill_package(recording, events) -> dict[str, Any]:
    ordered_events = [_coerce_event(event) for event in events]
    if not ordered_events:
        raise ValueError("Recording has no events to compile.")

    order_reference = _detect_order_reference(ordered_events)
    if order_reference is None:
        raise ValueError("Unsupported recording flow: order reference could not be detected.")

    if not _is_fake_erp_formula_review_flow(ordered_events, order_reference):
        raise ValueError("Unsupported recording flow: expected Fake ERP formula review flow.")

    return {
        "skill_id": "recorded_fake_erp_formula_review",
        "inputs": {"order_reference": "string"},
        "guards": ["formula_guard"],
        "workflow": [
            {"id": "open_orders", "type": "navigate", "target": "/fake-erp/sales/orders"},
            {
                "id": "search_order",
                "type": "fill",
                "selector": "[data-testid='order-search']",
                "value": "{{order_reference}}",
            },
            {
                "id": "open_order",
                "type": "click",
                "selector_template": "[data-testid='open-order-{{order_reference}}']",
            },
            {"id": "open_formula", "type": "click", "selector": "[data-testid='formula-tab']"},
            {"id": "review_formula", "type": "click", "selector": "[data-testid='review-formula']"},
            {"id": "run_formula_guard", "type": "guard", "guard": "formula_guard"},
        ],
        "llm_required_for_repeated_runs": False,
        "compiled_from_recording_id": recording.id,
    }


def _coerce_event(event) -> _EventView:
    return _EventView(
        event_type=_get(event, "event_type"),
        url=_get(event, "url"),
        page_title=_get(event, "page_title"),
        element_role=_get(event, "element_role"),
        element_text=_get(event, "element_text"),
        element_label=_get(event, "element_label"),
        selector=_get(event, "selector"),
        input_value=_get(event, "input_value"),
        before_text_snapshot=_get(event, "before_text_snapshot"),
        after_text_snapshot=_get(event, "after_text_snapshot"),
    )


def _detect_order_reference(events: list[_EventView]) -> str | None:
    for event in events:
        for candidate in _KNOWN_ORDER_REFERENCES:
            if any(_contains(value, candidate) for value in _event_text_values(event)):
                return candidate
    return None


def _is_fake_erp_formula_review_flow(events: list[_EventView], order_reference: str) -> bool:
    seen_selectors = {event.selector for event in events if event.selector}
    seen_events = {event.event_type for event in events}
    has_open_order = f"[data-testid='open-order-{order_reference}']" in seen_selectors
    has_formula_surface = "[data-testid='formula-tab']" in seen_selectors or "[data-testid='review-formula']" in seen_selectors
    has_interaction = {"click", "navigate"}.intersection(seen_events)
    return has_open_order and has_formula_surface and bool(has_interaction)


def _event_text_values(event: _EventView) -> list[str]:
    values = [
        event.url,
        event.page_title,
        event.element_role,
        event.element_text,
        event.element_label,
        event.selector,
        event.input_value,
        event.before_text_snapshot,
        event.after_text_snapshot,
    ]
    return [value for value in values if value]


def _contains(value: str, needle: str) -> bool:
    return needle.casefold() in value.casefold()


def _get(event, attribute: str):
    if isinstance(event, dict):
        return event.get(attribute)
    return getattr(event, attribute, None)
