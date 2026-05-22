from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_active_skill_run,
    list_active_skill_run_events,
    list_active_skill_runs_for_skill,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class ActiveSkillRunSummary:
    run_id: str
    version_id: str
    skill_id: str
    status: str
    actor: str
    trigger: str
    target_base_url: str
    replay_run_id: str | None
    inputs: dict = field(default_factory=dict)
    gate_result: dict = field(default_factory=dict)
    input_validation: dict = field(default_factory=dict)
    summary: dict = field(default_factory=dict)
    created_at: str = ""
    finished_at: str = ""


@dataclass(frozen=True)
class ActiveSkillRunEventEntry:
    event_id: str
    run_id: str
    event_type: str
    status: str
    detail: str
    payload: dict
    created_at: str


class ActiveSkillRunHistoryService:
    def get_run(self, run_id: str) -> ActiveSkillRunSummary | None:
        init_db()
        db = SessionLocal()
        try:
            row = get_active_skill_run(db, run_id)
            return self._to_summary(row) if row else None
        finally:
            db.close()

    def list_runs_for_skill(self, skill_id: str) -> list[ActiveSkillRunSummary]:
        init_db()
        db = SessionLocal()
        try:
            rows = list_active_skill_runs_for_skill(db, skill_id)
            return [self._to_summary(r) for r in rows]
        finally:
            db.close()

    def list_run_events(self, run_id: str) -> list[ActiveSkillRunEventEntry] | None:
        init_db()
        db = SessionLocal()
        try:
            run = get_active_skill_run(db, run_id)
            if run is None:
                return None
            rows = list_active_skill_run_events(db, run_id)
            return [
                ActiveSkillRunEventEntry(
                    event_id=r.id,
                    run_id=r.run_id,
                    event_type=r.event_type,
                    status=r.status,
                    detail=r.detail,
                    payload=json.loads(r.payload_json) if r.payload_json else {},
                    created_at=r.created_at.isoformat(),
                )
                for r in rows
            ]
        finally:
            db.close()

    def _to_summary(self, row) -> ActiveSkillRunSummary:
        return ActiveSkillRunSummary(
            run_id=row.id,
            version_id=row.version_id,
            skill_id=row.skill_id,
            status=row.status,
            actor=row.actor,
            trigger=row.trigger,
            target_base_url=row.target_base_url,
            replay_run_id=row.replay_run_id,
            inputs=json.loads(row.inputs_json) if row.inputs_json else {},
            gate_result=json.loads(row.gate_result_json) if row.gate_result_json else {},
            input_validation=json.loads(row.input_validation_json) if row.input_validation_json else {},
            summary=json.loads(row.summary_json) if row.summary_json else {},
            created_at=row.created_at.isoformat(),
            finished_at=row.finished_at.isoformat() if row.finished_at else "",
        )
