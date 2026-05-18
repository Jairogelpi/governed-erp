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
        raise ValueError("unsupported_fake_erp_formula_flow")

    order_reference = _validate_fake_erp_formula_review_sequence(ordered_events)

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


def _validate_fake_erp_formula_review_sequence(events: list[_EventView]) -> str:
    navigation_index = _find_event_index(
        events,
        start=0,
        predicate=lambda event: event.event_type == "navigate"
        and _contains(event.url or "", "/fake-erp/sales/orders"),
    )
    if navigation_index is None:
        raise ValueError("missing_sales_orders_navigation")

    search_index = _find_event_index(
        events,
        start=navigation_index + 1,
        predicate=lambda event: event.event_type == "fill"
        and event.selector == "[data-testid='order-search']",
    )
    if search_index is None:
        raise ValueError("missing_order_search_event")

    order_reference = _supported_order_reference_from_event(events[search_index])
    if order_reference is None:
        raise ValueError("unsupported_order_reference")

    open_order_index = _find_event_index(
        events,
        start=search_index + 1,
        predicate=lambda event: event.event_type == "click"
        and event.selector == f"[data-testid='open-order-{order_reference}']",
    )
    if open_order_index is None:
        raise ValueError("missing_open_order_event")

    formula_tab_index = _find_event_index(
        events,
        start=open_order_index + 1,
        predicate=lambda event: event.event_type == "click"
        and event.selector == "[data-testid='formula-tab']",
    )
    if formula_tab_index is None:
        raise ValueError("missing_formula_tab_event")

    review_formula_index = _find_event_index(
        events,
        start=formula_tab_index + 1,
        predicate=lambda event: event.event_type == "click"
        and event.selector == "[data-testid='review-formula']",
    )
    if review_formula_index is None:
        raise ValueError("missing_review_formula_event")

    if not all(_contains(event.url or "", "/fake-erp/") for event in events if event.url):
        raise ValueError("unsupported_fake_erp_formula_flow")

    return order_reference


def _find_event_index(events: list[_EventView], *, start: int, predicate) -> int | None:
    for index in range(start, len(events)):
        if predicate(events[index]):
            return index
    return None


def _supported_order_reference_from_event(event: _EventView) -> str | None:
    values = [event.input_value, event.element_text, event.selector, event.url, event.page_title]
    for candidate in _KNOWN_ORDER_REFERENCES:
        if any(_contains(value, candidate) for value in values if value):
            return candidate
    return None


def _contains(value: str, needle: str) -> bool:
    return needle.casefold() in value.casefold()


def _get(event, attribute: str):
    if isinstance(event, dict):
        return event.get(attribute)
    return getattr(event, attribute, None)
