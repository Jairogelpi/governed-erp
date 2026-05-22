from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from erpguard.db.repositories import list_recent_queue_entries_for_schedule
from erpguard.db.session import SessionLocal, init_db

_BLOCKING_STATUSES = frozenset({"queued", "dispatching", "dispatched", "completed"})


@dataclass(frozen=True)
class DedupDecision:
    is_duplicate: bool
    reason: str
    matched_entry_id: str | None = None


class SkillRunDedupService:
    def check(
        self,
        schedule_id: str,
        inputs: dict,
        dedup_window_seconds: int,
        now: datetime | None = None,
    ) -> DedupDecision:
        now = now or datetime.now(timezone.utc)
        since = now - timedelta(seconds=dedup_window_seconds)
        init_db()
        db = SessionLocal()
        try:
            recent = list_recent_queue_entries_for_schedule(db, schedule_id, since)
            target_payload = json.dumps(inputs or {}, sort_keys=True, default=str)
            for entry in recent:
                if entry.status not in _BLOCKING_STATUSES:
                    continue
                entry_payload = json.dumps(json.loads(entry.inputs_json or "{}"), sort_keys=True, default=str)
                if entry_payload == target_payload:
                    return DedupDecision(
                        is_duplicate=True,
                        reason=f"identical_inputs_within_{dedup_window_seconds}s",
                        matched_entry_id=entry.id,
                    )
            return DedupDecision(is_duplicate=False, reason="no_recent_duplicate")
        finally:
            db.close()
