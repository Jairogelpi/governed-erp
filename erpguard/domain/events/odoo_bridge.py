from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy.orm import Session

from erpguard.domain.events.ocel_service import OcelEventService


SUPPORTED_EVENT_TYPES = {
    "sale.order.created",
    "sale.order.updated",
    "sale.order.confirmed",
    "res.partner.created",
    "product.product.updated",
}
BLOCKED_EVENT_WORDS = {"create", "write", "update", "delete", "confirm", "post", "cancel"}
SECRET_KEYS = {"api_key", "password", "token", "secret"}


class OdooBridgeEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(min_length=1, max_length=200)
    event_type: str = Field(min_length=1, max_length=200)
    model: str = Field(min_length=1, max_length=200)
    record_id: int = Field(gt=0)
    occurred_at: str = Field(min_length=1, max_length=100)
    values: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = Field(default=None, max_length=200)
    historical: bool = False
    synthetic: bool = False

    @model_validator(mode="after")
    def validate_event_type(self) -> "OdooBridgeEvent":
        if self.event_type not in SUPPORTED_EVENT_TYPES:
            if any(word in self.event_type.lower().split(".") for word in BLOCKED_EVENT_WORDS):
                raise ValueError("unsupported_event_type:write_like_event")
            raise ValueError("unsupported_event_type")
        if self.historical and self.synthetic:
            raise ValueError("historical_and_synthetic_are_exclusive")
        return self


@dataclass(frozen=True)
class OdooIngestionResult:
    correlation_id: str
    created_events: int
    duplicate_events: int
    created_objects: int
    duplicate_objects: int


@dataclass(frozen=True)
class OdooPollResult:
    events: int
    duplicates: int
    cursor: str | None


def _safe_values(values: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in values.items() if key.lower() not in SECRET_KEYS}


def normalize_odoo_event(event: OdooBridgeEvent) -> dict[str, Any]:
    correlation_id = event.correlation_id or f"odoo:{event.event_id}"
    object_key = f"odoo:{event.model}:{event.record_id}"
    return {
        "ocel:global-event": {"ocel:activity": "erpguard.odoo_bridge", "ocel:version": "2.0"},
        "ocel:objects": {
            object_key: {"ocel:type": event.model, "ocel:ovmap": {"id": event.record_id}}
        },
        "ocel:events": {
            f"odoo:{event.event_id}": {
                "ocel:activity": event.event_type,
                "ocel:timestamp": event.occurred_at,
                "ocel:omap": [object_key],
                "ocel:vmap": {
                    **_safe_values(event.values),
                    "correlation_id": correlation_id,
                    "historical": event.historical,
                    "synthetic": event.synthetic,
                    "source_model": event.model,
                    "source_record_id": event.record_id,
                },
            }
        },
    }


class OdooEventIngestionService:
    def __init__(self, session: Session):
        self.session = session
        self.ocel = OcelEventService(session)

    def ingest_event(self, *, tenant_id: str, payload: dict[str, Any]) -> OdooIngestionResult:
        event = OdooBridgeEvent.model_validate(payload)
        result = self.ocel.import_ocel(
            tenant_id=tenant_id, document=normalize_odoo_event(event), source="odoo-bridge"
        )
        return OdooIngestionResult(
            correlation_id=event.correlation_id or f"odoo:{event.event_id}",
            created_events=result.created_events,
            duplicate_events=result.duplicate_events,
            created_objects=result.created_objects,
            duplicate_objects=result.duplicate_objects,
        )

    def ingest_poll(
        self, *, tenant_id: str, payloads: list[dict[str, Any]], cursor: str | None
    ) -> OdooPollResult:
        created = duplicates = 0
        for payload in payloads:
            result = self.ingest_event(tenant_id=tenant_id, payload=payload)
            created += result.created_events
            duplicates += result.duplicate_events
        if cursor is not None:
            self.ocel.save_cursor(tenant_id=tenant_id, connector_id="odoo", stream_key="events", value=cursor)
        return OdooPollResult(events=created, duplicates=duplicates, cursor=cursor)

    def export_events(self, *, tenant_id: str) -> dict[str, Any]:
        return self.ocel.export_ocel(tenant_id=tenant_id)
