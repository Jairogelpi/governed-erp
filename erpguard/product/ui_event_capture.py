from __future__ import annotations

import json
from dataclasses import dataclass

from erpguard.db.repositories import (
    add_ui_recording_event,
    list_ui_recording_events,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class UICapturedEvent:
    event_id: str
    session_id: str
    event_index: int
    event_type: str
    url: str | None
    selector: str | None
    element_text: str | None
    element_label: str | None
    input_value: str | None
    metadata: dict
    created_at: str


class UIEventCaptureService:
    def capture_event(
        self,
        session_id: str,
        event_type: str,
        url: str | None = None,
        selector: str | None = None,
        element_text: str | None = None,
        element_label: str | None = None,
        input_value: str | None = None,
        metadata: dict | None = None,
    ) -> UICapturedEvent:
        init_db()
        db = SessionLocal()
        try:
            row = add_ui_recording_event(
                db,
                session_id=session_id,
                event_type=event_type,
                url=url,
                selector=selector,
                element_text=element_text,
                element_label=element_label,
                input_value=input_value,
                metadata_json=json.dumps(metadata or {}, default=str),
            )
            return self._to_result(row, session_id)
        finally:
            db.close()

    def list_events(self, session_id: str) -> list[UICapturedEvent]:
        init_db()
        db = SessionLocal()
        try:
            rows = list_ui_recording_events(db, session_id)
            return [self._to_result(r, session_id) for r in rows]
        finally:
            db.close()

    def _to_result(self, row, session_id: str) -> UICapturedEvent:
        return UICapturedEvent(
            event_id=row.id,
            session_id=session_id,
            event_index=row.event_index,
            event_type=row.event_type,
            url=row.url,
            selector=row.selector,
            element_text=row.element_text,
            element_label=row.element_label,
            input_value=row.input_value,
            metadata=json.loads(row.metadata_json) if row.metadata_json else {},
            created_at=row.created_at.isoformat(),
        )
