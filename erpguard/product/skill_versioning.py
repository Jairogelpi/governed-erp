from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    create_ui_skill_version_record,
    create_ui_skill_version_lifecycle_event,
    get_ui_compiled_skill,
    get_ui_skill_version_record,
    list_ui_skill_version_records,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class UISkillVersionDetail:
    version_id: str
    skill_id: str
    compiled_skill_id: str
    version_number: int
    name: str
    status: str
    steps: list[dict] = field(default_factory=list)
    guard_names: list[str] = field(default_factory=list)
    replay_run_id: str | None = None
    promotion_readiness: dict = field(default_factory=dict)
    llm_required: bool = False
    runtime_type: str = "deterministic_ui"
    is_active: bool = False
    created_at: str = ""
    updated_at: str = ""


class UISkillVersioningService:
    def create_from_compiled_skill(
        self,
        compiled_skill_id: str,
        skill_id: str | None = None,
        replay_run_id: str | None = None,
    ) -> UISkillVersionDetail:
        init_db()
        db = SessionLocal()
        try:
            skill = get_ui_compiled_skill(db, compiled_skill_id)
            if skill is None:
                raise ValueError(f"Compiled skill '{compiled_skill_id}' not found.")

            derived_skill_id = skill_id or f"ui_skill_family_{skill.session_id}"

            row = create_ui_skill_version_record(
                db,
                skill_id=derived_skill_id,
                compiled_skill_id=compiled_skill_id,
                name=skill.name,
                steps_json=skill.steps_json,
                guard_names_json=skill.guard_names_json,
                replay_run_id=replay_run_id,
            )
            create_ui_skill_version_lifecycle_event(
                db,
                version_id=row.id,
                skill_id=row.skill_id,
                event_type="created",
                from_status="none",
                to_status="draft",
                actor="system",
                reason="created_from_compiled_ui_skill",
            )
            return self._to_detail(row)
        finally:
            db.close()

    def get_version(self, version_id: str) -> UISkillVersionDetail | None:
        init_db()
        db = SessionLocal()
        try:
            row = get_ui_skill_version_record(db, version_id)
            return self._to_detail(row) if row else None
        finally:
            db.close()

    def list_versions(self, skill_id: str) -> list[UISkillVersionDetail]:
        init_db()
        db = SessionLocal()
        try:
            return [self._to_detail(r) for r in list_ui_skill_version_records(db, skill_id)]
        finally:
            db.close()

    def _to_detail(self, row) -> UISkillVersionDetail:
        return UISkillVersionDetail(
            version_id=row.id,
            skill_id=row.skill_id,
            compiled_skill_id=row.compiled_skill_id,
            version_number=row.version_number,
            name=row.name,
            status=row.status,
            steps=json.loads(row.steps_json),
            guard_names=json.loads(row.guard_names_json),
            replay_run_id=row.replay_run_id,
            promotion_readiness=json.loads(row.promotion_readiness_json) if row.promotion_readiness_json else {},
            llm_required=row.llm_required,
            runtime_type=row.runtime_type,
            is_active=row.is_active,
            created_at=row.created_at.isoformat(),
            updated_at=row.updated_at.isoformat(),
        )
