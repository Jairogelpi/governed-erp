from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class NextRunPlan:
    schedule_id: str
    interval_seconds: int
    last_run_at: datetime | None
    next_run_at: datetime
    reason: str


class SkillSchedulePlannerService:
    def compute_next_run(
        self,
        schedule_id: str,
        interval_seconds: int,
        last_run_at: datetime | None,
        now: datetime | None = None,
    ) -> NextRunPlan:
        now = now or datetime.now(timezone.utc)
        if last_run_at is None:
            next_at = now
            reason = "no_previous_run_schedule_now"
        else:
            candidate = last_run_at + timedelta(seconds=interval_seconds)
            if candidate <= now:
                next_at = now
                reason = "interval_already_elapsed_schedule_now"
            else:
                next_at = candidate
                reason = "interval_in_future"
        return NextRunPlan(
            schedule_id=schedule_id,
            interval_seconds=interval_seconds,
            last_run_at=last_run_at,
            next_run_at=next_at,
            reason=reason,
        )
