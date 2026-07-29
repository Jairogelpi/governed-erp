from __future__ import annotations

from erpguard.recording_pipeline.ui_recording_normalizer import NormalizedEvent
from erpguard.recording_pipeline.ui_selector_extractor import UISelectorExtractorService


def _ev(idx: int, event_type: str, selector: str | None = None, label: str | None = None, value: str | None = None, url: str | None = None) -> NormalizedEvent:
    return NormalizedEvent(
        event_index=idx,
        event_type=event_type,
        url=url,
        selector=selector,
        element_text=None,
        element_label=label,
        input_value=value,
        metadata={},
    )


def test_extract_selectors_from_events():
    svc = UISelectorExtractorService()
    events = [
        _ev(0, "navigate", url="http://localhost:8000/fake-erp/orders"),
        _ev(1, "fill", selector="[data-testid='order-search']", value="SO-VALID"),
        _ev(2, "click", selector="[data-testid='open-order-SO-VALID']"),
    ]
    selectors = svc.extract_selectors(events)
    assert len(selectors) == 2
    assert selectors[0].selector == "[data-testid='order-search']"
    assert selectors[0].step_id == "step_1"
    assert selectors[1].selector == "[data-testid='open-order-SO-VALID']"


def test_no_selectors_for_navigate_without_selector():
    svc = UISelectorExtractorService()
    events = [_ev(0, "navigate", url="http://localhost:8000/fake-erp/orders")]
    selectors = svc.extract_selectors(events)
    assert len(selectors) == 0


def test_build_selector_map():
    svc = UISelectorExtractorService()
    events = [
        _ev(0, "navigate"),
        _ev(1, "fill", selector="[data-testid='search']"),
        _ev(2, "click", selector="[data-testid='submit']"),
    ]
    smap = svc.build_selector_map(events)
    assert smap == {"step_1": "[data-testid='search']", "step_2": "[data-testid='submit']"}


def test_extract_selector_with_label():
    svc = UISelectorExtractorService()
    events = [_ev(0, "fill", selector="[name='qty']", label="Quantity", value="10")]
    selectors = svc.extract_selectors(events)
    assert selectors[0].label == "Quantity"
    assert selectors[0].input_value == "10"
