from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from erpguard.db.repositories import get_skill_schedule, update_skill_schedule
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class LockAcquireResult:
    acquired: bool
    schedule_id: str
    token: str | None
    locked_until: datetime | None
    reason: str


class SkillRunLockService:
    _DEFAULT_TTL_SECONDS = 300

    def acquire(
        self,
        schedule_id: str,
        ttl_seconds: int | None = None,
        now: datetime | None = None,
    ) -> LockAcquireResult:
        now = now or datetime.now(timezone.utc)
        ttl = ttl_seconds if ttl_seconds is not None else self._DEFAULT_TTL_SECONDS
        init_db()
        db = SessionLocal()
        try:
            schedule = get_skill_schedule(db, schedule_id)
            if schedule is None:
                return LockAcquireResult(acquired=False, schedule_id=schedule_id, token=None,
                                         locked_until=None, reason="schedule_not_found")

            if schedule.tick_lock_token and schedule.tick_lock_until:
                locked_until = schedule.tick_lock_until
                if locked_until.tzinfo is None:
                    locked_until = locked_until.replace(tzinfo=timezone.utc)
                if locked_until > now:
                    return LockAcquireResult(
                        acquired=False, schedule_id=schedule_id, token=None,
                        locked_until=locked_until,
                        reason="already_locked",
                    )

            token = f"lock_{uuid4().hex[:16]}"
            until = now + timedelta(seconds=ttl)
            update_skill_schedule(db, schedule_id, tick_lock_token=token, tick_lock_until=until)
            return LockAcquireResult(
                acquired=True, schedule_id=schedule_id, token=token,
                locked_until=until, reason="lock_acquired",
            )
        finally:
            db.close()

    def release(self, schedule_id: str, token: str) -> bool:
        init_db()
        db = SessionLocal()
        try:
            schedule = get_skill_schedule(db, schedule_id)
            if schedule is None:
                return False
            if schedule.tick_lock_token != token:
                return False
            update_skill_schedule(db, schedule_id, tick_lock_token=None, tick_lock_until=None)
            return True
        finally:
            db.close()
