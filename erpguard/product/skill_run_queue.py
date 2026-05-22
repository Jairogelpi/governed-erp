from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.db.repositories import (
    create_skill_run_queue_entry,
    get_skill_run_queue_entry,
    list_skill_run_queue_entries_for_schedule,
    update_skill_run_queue_entry,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class QueueEntry:
    entry_id: str
    schedule_id: str
    version_id: str
    skill_id: str
    status: str
    inputs: dict = field(default_factory=dict)
    target_base_url: str = ""
    run_id: str | None = None
    detail: str = ""
    enqueued_at: str = ""
    dispatched_at: str = ""
    finished_at: str = ""


class SkillRunQueueService:
    def enqueue(
        self,
        schedule_id: str,
        version_id: str,
        skill_id: str,
        inputs: dict,
        target_base_url: str,
        status: str = "queued",
        detail: str = "",
    ) -> QueueEntry:
        init_db()
        db = SessionLocal()
        try:
            row = create_skill_run_queue_entry(
                db,
                schedule_id=schedule_id,
                version_id=version_id,
                skill_id=skill_id,
                inputs_json=json.dumps(inputs or {}, default=str),
                target_base_url=target_base_url,
                status=status,
                detail=detail,
            )
            return self._to_entry(row)
        finally:
            db.close()

    def mark_dispatching(self, entry_id: str) -> QueueEntry | None:
        init_db()
        db = SessionLocal()
        try:
            row = update_skill_run_queue_entry(
                db, entry_id, status="dispatching",
                dispatched_at=datetime.now(timezone.utc),
            )
            return self._to_entry(row) if row else None
        finally:
            db.close()

    def mark_dispatched(self, entry_id: str, run_id: str, run_status: str, detail: str = "") -> QueueEntry | None:
        init_db()
        db = SessionLocal()
        try:
            mapped = {
                "completed": "completed",
                "completed_with_failures": "completed",
                "blocked": "failed",
                "rejected": "failed",
                "error": "failed",
            }.get(run_status, "dispatched")
            row = update_skill_run_queue_entry(
                db, entry_id, status=mapped, run_id=run_id, detail=detail,
                finished_at=datetime.now(timezone.utc),
            )
            return self._to_entry(row) if row else None
        finally:
            db.close()

    def mark_skipped(self, entry_id: str, reason: str, detail: str = "") -> QueueEntry | None:
        init_db()
        db = SessionLocal()
        try:
            status = "skipped_dedup" if reason == "dedup" else "skipped_killed" if reason == "killed" else "skipped"
            row = update_skill_run_queue_entry(
                db, entry_id, status=status, detail=detail,
                finished_at=datetime.now(timezone.utc),
            )
            return self._to_entry(row) if row else None
        finally:
            db.close()

    def get_entry(self, entry_id: str) -> QueueEntry | None:
        init_db()
        db = SessionLocal()
        try:
            row = get_skill_run_queue_entry(db, entry_id)
            return self._to_entry(row) if row else None
        finally:
            db.close()

    def list_for_schedule(self, schedule_id: str) -> list[QueueEntry]:
        init_db()
        db = SessionLocal()
        try:
            rows = list_skill_run_queue_entries_for_schedule(db, schedule_id)
            return [self._to_entry(r) for r in rows]
        finally:
            db.close()

    def _to_entry(self, row) -> QueueEntry:
        return QueueEntry(
            entry_id=row.id,
            schedule_id=row.schedule_id,
            version_id=row.version_id,
            skill_id=row.skill_id,
            status=row.status,
            inputs=json.loads(row.inputs_json) if row.inputs_json else {},
            target_base_url=row.target_base_url,
            run_id=row.run_id,
            detail=row.detail,
            enqueued_at=row.enqueued_at.isoformat() if row.enqueued_at else "",
            dispatched_at=row.dispatched_at.isoformat() if row.dispatched_at else "",
            finished_at=row.finished_at.isoformat() if row.finished_at else "",
        )
