from __future__ import annotations

import json
from dataclasses import dataclass

from erpguard.db.repositories import (
    add_skill_schedule_event,
    get_skill_schedule,
    list_skill_schedule_events,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class ScheduleEventEntry:
    event_id: str
    schedule_id: str
    event_type: str
    status: str
    detail: str
    payload: dict
    created_at: str


class SkillScheduleAuditService:
    def record(
        self,
        schedule_id: str,
        event_type: str,
        status: str = "info",
        detail: str = "",
        payload: dict | None = None,
    ) -> ScheduleEventEntry:
        init_db()
        db = SessionLocal()
        try:
            row = add_skill_schedule_event(
                db,
                schedule_id=schedule_id,
                event_type=event_type,
                status=status,
                detail=detail,
                payload_json=json.dumps(payload or {}, default=str),
            )
            return self._to_entry(row)
        finally:
            db.close()

    def list_events(self, schedule_id: str) -> list[ScheduleEventEntry] | None:
        init_db()
        db = SessionLocal()
        try:
            schedule = get_skill_schedule(db, schedule_id)
            if schedule is None:
                return None
            rows = list_skill_schedule_events(db, schedule_id)
            return [self._to_entry(r) for r in rows]
        finally:
            db.close()

    def _to_entry(self, row) -> ScheduleEventEntry:
        return ScheduleEventEntry(
            event_id=row.id,
            schedule_id=row.schedule_id,
            event_type=row.event_type,
            status=row.status,
            detail=row.detail,
            payload=json.loads(row.payload_json) if row.payload_json else {},
            created_at=row.created_at.isoformat(),
        )
