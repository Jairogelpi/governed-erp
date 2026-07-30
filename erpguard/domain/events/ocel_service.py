from __future__ import annotations

import json
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy.orm import Session

from erpguard.db.model_packages.events import CanonicalEvent, CanonicalObject, IngestionCursor
from erpguard.db.model_packages.event_links import CanonicalEventObject


OBJECT_TYPE_ALIASES = {
    "sale.order": "sales_order",
    "sale_order": "sales_order",
    "res.partner": "customer",
    "customer": "customer",
    "product.product": "product",
    "product": "product",
}


@dataclass(frozen=True)
class OcelImportSummary:
    created_events: int = 0
    duplicate_events: int = 0
    created_objects: int = 0
    duplicate_objects: int = 0
    shadow_deployments: int = 0
    shadow_evaluations: int = 0
    shadow_deduplications: int = 0
    shadow_failures: int = 0


class OcelEventService:
    def __init__(self, session: Session):
        self.session = session

    def import_ocel(self, *, tenant_id: str, document: dict, source: str) -> OcelImportSummary:
        objects = document.get("ocel:objects", {})
        events = document.get("ocel:events", {})
        created_objects = duplicate_objects = 0
        for object_key, raw in objects.items():
            existing_object = (
                self.session.query(CanonicalObject)
                .filter_by(tenant_id=tenant_id, object_key=str(object_key))
                .one_or_none()
            )
            if existing_object:
                duplicate_objects += 1
                continue
            object_type = OBJECT_TYPE_ALIASES.get(str(raw.get("ocel:type", "unknown")), str(raw.get("ocel:type", "unknown")))
            self.session.add(CanonicalObject(
                id=f"obj_{tenant_id}_{object_key}", tenant_id=tenant_id,
                object_type=object_type, object_key=str(object_key),
                attributes_json=json.dumps(raw.get("ocel:ovmap", {}), sort_keys=True),
            ))
            created_objects += 1
        self.session.flush()

        created_events = duplicate_events = 0
        for event_key, raw in events.items():
            event_key = str(event_key)
            existing_event = (
                self.session.query(CanonicalEvent)
                .filter_by(tenant_id=tenant_id, event_key=event_key)
                .one_or_none()
            )
            if existing_event:
                duplicate_events += 1
                continue
            canonical_event = CanonicalEvent(
                id=f"evt_{tenant_id}_{event_key}", tenant_id=tenant_id, event_key=event_key,
                event_type=str(raw.get("ocel:activity", "unknown")),
                event_timestamp=str(raw.get("ocel:timestamp", "")), source=source,
                object_keys_json=json.dumps([str(item) for item in raw.get("ocel:omap", [])]),
                attributes_json=json.dumps(raw.get("ocel:vmap", {}), sort_keys=True),
            )
            self.session.add(canonical_event)
            for object_key in [str(item) for item in raw.get("ocel:omap", [])]:
                object_row = (
                    self.session.query(CanonicalObject)
                    .filter_by(tenant_id=tenant_id, object_key=object_key)
                    .one_or_none()
                )
                if object_row is not None:
                    self.session.add(CanonicalEventObject(
                        id=f"link_{canonical_event.id}_{object_row.id}",
                        tenant_id=tenant_id, event_id=canonical_event.id,
                        object_id=object_row.id, qualifier="",
                    ))
            created_events += 1
        self.session.commit()
        affected_object_keys = sorted(
            {
                str(object_key)
                for raw in events.values()
                for object_key in raw.get("ocel:omap", [])
            }
        )
        from erpguard.domain.shadow.operational_feed import OperationalShadowFeedService

        shadow = OperationalShadowFeedService(self.session).process_applicable_deployments(
            tenant_id=tenant_id,
            object_keys=affected_object_keys,
        )
        return OcelImportSummary(
            created_events,
            duplicate_events,
            created_objects,
            duplicate_objects,
            shadow.deployment_count,
            shadow.evaluated_case_count,
            shadow.deduplicated_case_count,
            shadow.failed_case_count,
        )

    def export_ocel(self, *, tenant_id: str) -> dict:
        objects = (
            self.session.query(CanonicalObject)
            .filter_by(tenant_id=tenant_id)
            .order_by(CanonicalObject.object_key.asc())
            .all()
        )
        events = (
            self.session.query(CanonicalEvent)
            .filter_by(tenant_id=tenant_id)
            .order_by(CanonicalEvent.event_key.asc())
            .all()
        )
        return {
            "ocel:global-event": {"ocel:activity": "erpguard.export", "ocel:version": "2.0"},
            "ocel:objects": {
                item.object_key: {
                    "ocel:type": item.object_type,
                    "ocel:ovmap": json.loads(item.attributes_json),
                }
                for item in objects
            },
            "ocel:events": {
                item.event_key: {
                    "ocel:activity": item.event_type,
                    "ocel:timestamp": item.event_timestamp,
                    "ocel:omap": json.loads(item.object_keys_json),
                    "ocel:vmap": json.loads(item.attributes_json),
                }
                for item in events
            },
        }

    def save_cursor(self, *, tenant_id: str, connector_id: str, stream_key: str, value: str) -> None:
        cursor = (
            self.session.query(IngestionCursor)
            .filter_by(tenant_id=tenant_id, connector_id=connector_id, stream_key=stream_key)
            .one_or_none()
        )
        if cursor is None:
            cursor = IngestionCursor(
                id=f"cursor_{uuid4().hex}", tenant_id=tenant_id,
                connector_id=connector_id, stream_key=stream_key, cursor_value=value,
            )
            self.session.add(cursor)
        else:
            cursor.cursor_value = value
        self.session.commit()

    def get_cursor(self, tenant_id: str, connector_id: str, stream_key: str) -> str | None:
        cursor = (
            self.session.query(IngestionCursor)
            .filter_by(tenant_id=tenant_id, connector_id=connector_id, stream_key=stream_key)
            .one_or_none()
        )
        return cursor.cursor_value if cursor else None
