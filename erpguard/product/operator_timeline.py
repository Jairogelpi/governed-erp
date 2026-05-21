from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import get_operator_session, list_operator_session_events


class OperatorTimelineService:
    def __init__(self, session) -> None:
        self.session = session

    def get_timeline(self, session_id: str) -> dict:
        row = get_operator_session(self.session, session_id)
        if row is None:
            raise ObjectNotFoundError(f"Operator session '{session_id}' not found.")
        events = list_operator_session_events(self.session, session_id)
        return {
            "session_id": session_id,
            "current_step": row.current_step,
            "status": row.status,
            "events": [
                {
                    "event_id": ev.id,
                    "step": ev.step,
                    "status": ev.status,
                    "detail": json.loads(ev.detail_json),
                    "created_at": ev.created_at.isoformat(),
                }
                for ev in events
            ],
            "steps_completed": [ev.step for ev in events if ev.status == "ok"],
            "steps_errored": [ev.step for ev in events if ev.status == "error"],
        }
