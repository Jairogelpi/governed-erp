from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class NormalizedEvent:
    event_index: int
    event_type: str
    url: str | None
    selector: str | None
    element_text: str | None
    element_label: str | None
    input_value: str | None
    metadata: dict


@dataclass(frozen=True)
class NormalizedRecording:
    session_id: str
    event_count: int
    events: list[NormalizedEvent] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)


class UIRecordingNormalizerService:
    _DROPPABLE_TYPES = frozenset({"mousemove", "scroll", "focus", "blur", "keyup"})

    def normalize(self, session_id: str, events: list) -> NormalizedRecording:
        filtered = [e for e in events if self._get(e, "event_type") not in self._DROPPABLE_TYPES]
        seen_selectors: set[tuple[str, str | None]] = set()
        deduped: list = []
        for ev in filtered:
            key = (self._get(ev, "event_type") or "", self._get(ev, "selector"))
            if key[0] in {"navigate", "fill", "click", "guard"}:
                if key not in seen_selectors:
                    seen_selectors.add(key)
                    deduped.append(ev)
            else:
                deduped.append(ev)

        normalized: list[NormalizedEvent] = [
            NormalizedEvent(
                event_index=idx,
                event_type=self._get(ev, "event_type") or "unknown",
                url=self._get(ev, "url"),
                selector=self._get(ev, "selector"),
                element_text=self._get(ev, "element_text"),
                element_label=self._get(ev, "element_label"),
                input_value=self._get(ev, "input_value"),
                metadata=self._get(ev, "metadata") or {},
            )
            for idx, ev in enumerate(deduped)
        ]

        diagnostics: list[str] = []
        if not normalized:
            diagnostics.append("no_events_after_normalization")

        return NormalizedRecording(
            session_id=session_id,
            event_count=len(normalized),
            events=normalized,
            diagnostics=diagnostics,
        )

    def _get(self, obj, attr: str):
        if isinstance(obj, dict):
            return obj.get(attr)
        return getattr(obj, attr, None)
