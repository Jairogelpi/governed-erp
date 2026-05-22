from __future__ import annotations

from dataclasses import dataclass

from erpguard.product.ui_recording_normalizer import NormalizedEvent


@dataclass(frozen=True)
class ExtractedSelector:
    step_id: str
    event_type: str
    selector: str
    label: str | None
    input_value: str | None
    url: str | None


class UISelectorExtractorService:
    def extract_selectors(self, events: list[NormalizedEvent]) -> list[ExtractedSelector]:
        selectors: list[ExtractedSelector] = []
        for ev in events:
            if ev.selector:
                selectors.append(
                    ExtractedSelector(
                        step_id=f"step_{ev.event_index}",
                        event_type=ev.event_type,
                        selector=ev.selector,
                        label=ev.element_label or ev.element_text,
                        input_value=ev.input_value,
                        url=ev.url,
                    )
                )
        return selectors

    def build_selector_map(self, events: list[NormalizedEvent]) -> dict[str, str]:
        return {
            f"step_{ev.event_index}": ev.selector
            for ev in events
            if ev.selector
        }
