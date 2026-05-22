from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.db.repositories import (
    list_due_active_skill_schedules,
    update_skill_schedule,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.active_skill_runner import ActiveSkillRunnerService
from erpguard.product.skill_run_dedup import SkillRunDedupService
from erpguard.product.skill_run_lock import SkillRunLockService
from erpguard.product.skill_run_queue import SkillRunQueueService
from erpguard.product.skill_schedule_audit import SkillScheduleAuditService
from erpguard.product.skill_schedule_planner import SkillSchedulePlannerService


@dataclass(frozen=True)
class TickDispatch:
    schedule_id: str
    queue_entry_id: str
    run_id: str
    run_status: str


@dataclass(frozen=True)
class TickSkip:
    schedule_id: str
    reason: str
    detail: str = ""


@dataclass(frozen=True)
class TickFailure:
    schedule_id: str
    error: str


@dataclass(frozen=True)
class TickReport:
    now: str
    due_count: int
    dispatched: list[TickDispatch] = field(default_factory=list)
    skipped: list[TickSkip] = field(default_factory=list)
    failed: list[TickFailure] = field(default_factory=list)


class SkillScheduleTickService:
    _dedup = SkillRunDedupService()
    _lock = SkillRunLockService()
    _queue = SkillRunQueueService()
    _audit = SkillScheduleAuditService()
    _planner = SkillSchedulePlannerService()
    _runner = ActiveSkillRunnerService()

    def tick(self, now: datetime | None = None) -> TickReport:
        now = now or datetime.now(timezone.utc)

        init_db()
        db = SessionLocal()
        try:
            due_schedules = list_due_active_skill_schedules(db, now)
            schedule_snapshots = [
                {
                    "id": s.id,
                    "version_id": s.version_id,
                    "skill_id": s.skill_id,
                    "interval_seconds": s.interval_seconds,
                    "min_interval_seconds": s.min_interval_seconds,
                    "dedup_window_seconds": s.dedup_window_seconds,
                    "target_base_url": s.target_base_url,
                    "inputs_json": s.inputs_json,
                    "last_run_at": s.last_run_at,
                }
                for s in due_schedules
            ]
        finally:
            db.close()

        dispatched: list[TickDispatch] = []
        skipped: list[TickSkip] = []
        failed: list[TickFailure] = []

        for snap in schedule_snapshots:
            sid = snap["id"]
            inputs = json.loads(snap["inputs_json"] or "{}")

            # 1. Acquire lock
            lock = self._lock.acquire(sid, now=now)
            if not lock.acquired:
                self._audit.record(sid, "tick_skipped_locked", status="warning",
                                   detail=lock.reason, payload={"locked_until": lock.locked_until.isoformat() if lock.locked_until else None})
                skipped.append(TickSkip(schedule_id=sid, reason="locked", detail=lock.reason))
                continue

            try:
                # 2. Min interval check
                if snap["last_run_at"] is not None:
                    last_run = snap["last_run_at"]
                    if last_run.tzinfo is None:
                        last_run = last_run.replace(tzinfo=timezone.utc)
                    elapsed = (now - last_run).total_seconds()
                    if elapsed < snap["min_interval_seconds"]:
                        self._audit.record(sid, "tick_skipped_min_interval", status="warning",
                                           detail=f"elapsed={elapsed:.1f}s < min_interval={snap['min_interval_seconds']}s",
                                           payload={"elapsed_seconds": elapsed})
                        skipped.append(TickSkip(schedule_id=sid, reason="min_interval",
                                                detail=f"elapsed={elapsed:.1f}s"))
                        self._lock.release(sid, lock.token)
                        continue

                # 3. Dedup check
                dedup = self._dedup.check(sid, inputs, snap["dedup_window_seconds"], now=now)
                if dedup.is_duplicate:
                    entry = self._queue.enqueue(
                        sid, snap["version_id"], snap["skill_id"], inputs,
                        snap["target_base_url"], status="skipped_dedup",
                        detail=dedup.reason,
                    )
                    self._audit.record(sid, "tick_skipped_dedup", status="warning",
                                       detail=dedup.reason, payload={"matched_entry_id": dedup.matched_entry_id, "queue_entry_id": entry.entry_id})
                    skipped.append(TickSkip(schedule_id=sid, reason="dedup", detail=dedup.reason))
                    self._lock.release(sid, lock.token)
                    continue

                # 4. Enqueue
                entry = self._queue.enqueue(
                    sid, snap["version_id"], snap["skill_id"], inputs,
                    snap["target_base_url"], status="queued",
                )
                self._audit.record(sid, "tick_enqueued", status="ok",
                                   detail=f"Queue entry {entry.entry_id} created",
                                   payload={"queue_entry_id": entry.entry_id})

                # 5. Dispatch through ActiveSkillRunner
                self._queue.mark_dispatching(entry.entry_id)
                self._audit.record(sid, "tick_dispatching", status="info",
                                   detail=f"Dispatching queue entry {entry.entry_id}",
                                   payload={"queue_entry_id": entry.entry_id})

                run = self._runner.run(
                    version_id=snap["version_id"],
                    target_base_url=snap["target_base_url"],
                    actor=f"scheduler:{sid}",
                    inputs=inputs,
                )

                self._queue.mark_dispatched(entry.entry_id, run.run_id, run.status,
                                            detail=run.summary)

                # 6. Update schedule next_run_at / last_run_at
                plan = self._planner.compute_next_run(sid, snap["interval_seconds"], now, now=now)
                init_db()
                db2 = SessionLocal()
                try:
                    update_skill_schedule(
                        db2, sid,
                        last_run_at=now,
                        last_run_id=run.run_id,
                        next_run_at=plan.next_run_at,
                    )
                finally:
                    db2.close()

                self._audit.record(sid, "tick_dispatched", status="ok",
                                   detail=f"Run {run.run_id} status={run.status}",
                                   payload={"run_id": run.run_id, "queue_entry_id": entry.entry_id,
                                            "run_status": run.status, "next_run_at": plan.next_run_at.isoformat()})

                dispatched.append(TickDispatch(
                    schedule_id=sid, queue_entry_id=entry.entry_id,
                    run_id=run.run_id, run_status=run.status,
                ))

            except Exception as exc:
                self._audit.record(sid, "tick_failed", status="error",
                                   detail=str(exc), payload={"error": str(exc)})
                failed.append(TickFailure(schedule_id=sid, error=str(exc)))
            finally:
                self._lock.release(sid, lock.token)

        return TickReport(
            now=now.isoformat(),
            due_count=len(schedule_snapshots),
            dispatched=dispatched,
            skipped=skipped,
            failed=failed,
        )
