from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from erpguard.db.model_packages.event_links import CanonicalEventObject
from erpguard.db.model_packages.events import CanonicalEvent, CanonicalObject


@dataclass(frozen=True)
class TraceEvent:
    event_key: str
    event_type: str
    timestamp: str


@dataclass(frozen=True)
class CaseTrace:
    case_id: str
    object_type: str
    variant_id: str
    events: tuple[TraceEvent, ...]
    duration_seconds: float | None


@dataclass(frozen=True)
class VariantSummary:
    variant_id: str
    sequence: tuple[str, ...]
    case_count: int
    duration_seconds: float | None
    case_ids: tuple[str, ...]


def _normalize_event_type(value: str) -> str:
    normalized = ".".join(part.strip().lower().replace(" ", "_") for part in value.split(".") if part.strip())
    return {
        "quote.created": "sales.quote.created",
        "quote.reviewed": "sales.quote.reviewed",
        "order.created": "sales.order.created",
    }.get(normalized, normalized)


def _duration(events: tuple[TraceEvent, ...]) -> float | None:
    if len(events) < 2:
        return 0.0 if events else None
    try:
        start = datetime.fromisoformat(events[0].timestamp.replace("Z", "+00:00"))
        end = datetime.fromisoformat(events[-1].timestamp.replace("Z", "+00:00"))
        return (end - start).total_seconds()
    except ValueError:
        return None


class VariantDiscoveryService:
    def __init__(self, session: Session):
        self.session = session

    def _traces(self, tenant_id: str, object_type: str) -> list[CaseTrace]:
        rows = (
            self.session.query(CanonicalObject, CanonicalEvent)
            .join(CanonicalEventObject, CanonicalEventObject.object_id == CanonicalObject.id)
            .join(CanonicalEvent, CanonicalEvent.id == CanonicalEventObject.event_id)
            .filter(
                CanonicalObject.tenant_id == tenant_id,
                CanonicalObject.object_type == object_type,
                CanonicalEventObject.tenant_id == tenant_id,
                CanonicalEvent.tenant_id == tenant_id,
            )
            .order_by(CanonicalObject.object_key.asc(), CanonicalEvent.event_timestamp.asc(), CanonicalEvent.created_at.asc())
            .all()
        )
        grouped: dict[str, tuple[CanonicalObject, list[TraceEvent]]] = {}
        for obj, event in rows:
            if obj.object_key not in grouped:
                grouped[obj.object_key] = (obj, [])
            grouped[obj.object_key][1].append(
                TraceEvent(
                    event_key=event.event_key,
                    event_type=_normalize_event_type(event.event_type),
                    timestamp=event.event_timestamp,
                )
            )
        result: list[CaseTrace] = []
        for obj, trace_events in grouped.values():
            sequence = tuple(item.event_type for item in trace_events)
            variant_id = "variant_" + hashlib.sha256("|".join(sequence).encode()).hexdigest()[:16]
            result.append(CaseTrace(obj.object_key, object_type, variant_id, tuple(trace_events), _duration(tuple(trace_events))))
        return result

    def discover(self, *, tenant_id: str, object_type: str) -> list[VariantSummary]:
        groups: dict[str, list[CaseTrace]] = {}
        for trace in self._traces(tenant_id, object_type):
            groups.setdefault(trace.variant_id, []).append(trace)
        summaries = []
        for variant_id, traces in groups.items():
            durations = [item.duration_seconds for item in traces if item.duration_seconds is not None]
            sequence = tuple(item.event_type for item in traces[0].events)
            summaries.append(
                VariantSummary(
                    variant_id=variant_id,
                    sequence=sequence,
                    case_count=len(traces),
                    duration_seconds=(sum(durations) / len(durations)) if durations else None,
                    case_ids=tuple(sorted(item.case_id for item in traces)),
                )
            )
        return sorted(summaries, key=lambda item: (-item.case_count, -len(item.sequence), item.sequence))

    def case_trace(self, *, tenant_id: str, case_id: str, object_type: str) -> CaseTrace:
        for trace in self._traces(tenant_id, object_type):
            if trace.case_id == case_id:
                return trace
        raise KeyError("case_not_found")
