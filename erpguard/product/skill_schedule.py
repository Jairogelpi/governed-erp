from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.db.repositories import (
    create_skill_schedule,
    get_skill_schedule,
    get_ui_skill_version_record,
    list_skill_schedules_for_skill,
    update_skill_schedule,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.skill_schedule_audit import SkillScheduleAuditService
from erpguard.product.skill_schedule_gate import SkillScheduleGateService
from erpguard.product.skill_schedule_planner import SkillSchedulePlannerService

_VALID_TRANSITIONS = {
    "draft":    {"active", "disabled"},
    "active":   {"paused", "disabled"},
    "paused":   {"active", "disabled"},
    "disabled": set(),
}


@dataclass(frozen=True)
class ScheduleDetail:
    schedule_id: str
    version_id: str
    skill_id: str
    name: str
    interval_seconds: int
    min_interval_seconds: int
    dedup_window_seconds: int
    status: str
    target_base_url: str
    inputs: dict = field(default_factory=dict)
    next_run_at: str = ""
    last_run_at: str = ""
    last_run_id: str | None = None
    created_by: str = ""
    created_at: str = ""
    updated_at: str = ""


class SkillScheduleService:
    _gate = SkillScheduleGateService()
    _planner = SkillSchedulePlannerService()
    _audit = SkillScheduleAuditService()

    def create_schedule(
        self,
        version_id: str,
        name: str,
        interval_seconds: int,
        target_base_url: str,
        min_interval_seconds: int = 60,
        dedup_window_seconds: int = 30,
        inputs: dict | None = None,
        created_by: str = "manual_operator",
    ) -> ScheduleDetail:
        gate = self._gate.check(version_id, target_base_url, interval_seconds, min_interval_seconds, dedup_window_seconds)
        if not gate.can_schedule:
            raise ValueError("Schedule gate blocked: " + "; ".join(gate.blocking_reasons))

        init_db()
        db = SessionLocal()
        try:
            version = get_ui_skill_version_record(db, version_id)
            row = create_skill_schedule(
                db,
                version_id=version_id,
                skill_id=version.skill_id,
                name=name,
                interval_seconds=interval_seconds,
                min_interval_seconds=min_interval_seconds,
                dedup_window_seconds=dedup_window_seconds,
                target_base_url=target_base_url,
                inputs_json=json.dumps(inputs or {}, default=str),
                created_by=created_by,
            )
        finally:
            db.close()

        self._audit.record(
            row.id, "created", status="ok",
            detail=f"Schedule created in 'draft' status with interval={interval_seconds}s",
            payload={"gate_checks": gate.checks},
        )
        return self._to_detail(row)

    def get_schedule(self, schedule_id: str) -> ScheduleDetail | None:
        init_db()
        db = SessionLocal()
        try:
            row = get_skill_schedule(db, schedule_id)
            return self._to_detail(row) if row else None
        finally:
            db.close()

    def list_schedules_for_skill(self, skill_id: str) -> list[ScheduleDetail]:
        init_db()
        db = SessionLocal()
        try:
            rows = list_skill_schedules_for_skill(db, skill_id)
            return [self._to_detail(r) for r in rows]
        finally:
            db.close()

    def transition(self, schedule_id: str, target_status: str, actor: str = "manual_operator", reason: str = "") -> ScheduleDetail:
        init_db()
        db = SessionLocal()
        try:
            row = get_skill_schedule(db, schedule_id)
            if row is None:
                raise ValueError(f"Schedule '{schedule_id}' not found.")
            from_status = row.status
            allowed = _VALID_TRANSITIONS.get(from_status, set())
            if target_status not in allowed:
                raise ValueError(
                    f"Cannot transition schedule from '{from_status}' to '{target_status}'. "
                    f"Allowed: {sorted(allowed) or 'none'}."
                )

            if target_status == "active" and row.next_run_at is None:
                plan = self._planner.compute_next_run(schedule_id, row.interval_seconds, row.last_run_at)
                update_skill_schedule(db, schedule_id, status=target_status, next_run_at=plan.next_run_at)
            else:
                update_skill_schedule(db, schedule_id, status=target_status)
            refreshed = get_skill_schedule(db, schedule_id)
        finally:
            db.close()

        self._audit.record(
            schedule_id, event_type=target_status, status="ok",
            detail=f"Schedule transitioned from '{from_status}' to '{target_status}' by {actor}. Reason: {reason}",
            payload={"actor": actor, "reason": reason},
        )
        return self._to_detail(refreshed)

    def activate(self, schedule_id: str, actor: str = "manual_operator", reason: str = "") -> ScheduleDetail:
        return self.transition(schedule_id, "active", actor=actor, reason=reason)

    def pause(self, schedule_id: str, actor: str = "manual_operator", reason: str = "") -> ScheduleDetail:
        return self.transition(schedule_id, "paused", actor=actor, reason=reason)

    def resume(self, schedule_id: str, actor: str = "manual_operator", reason: str = "") -> ScheduleDetail:
        return self.transition(schedule_id, "active", actor=actor, reason=reason)

    def disable(self, schedule_id: str, actor: str = "manual_operator", reason: str = "") -> ScheduleDetail:
        return self.transition(schedule_id, "disabled", actor=actor, reason=reason)

    def _to_detail(self, row) -> ScheduleDetail:
        return ScheduleDetail(
            schedule_id=row.id,
            version_id=row.version_id,
            skill_id=row.skill_id,
            name=row.name,
            interval_seconds=row.interval_seconds,
            min_interval_seconds=row.min_interval_seconds,
            dedup_window_seconds=row.dedup_window_seconds,
            status=row.status,
            target_base_url=row.target_base_url,
            inputs=json.loads(row.inputs_json) if row.inputs_json else {},
            next_run_at=row.next_run_at.isoformat() if row.next_run_at else "",
            last_run_at=row.last_run_at.isoformat() if row.last_run_at else "",
            last_run_id=row.last_run_id,
            created_by=row.created_by,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
