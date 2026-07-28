from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_ui_skill_version_record,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class RollbackPlan:
    current_version_id: str
    target_version_id: str
    skill_id: str
    current_version_number: int
    target_version_number: int
    current_status: str
    target_status: str
    is_executable: bool
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    impact_summary: str = ""
    step_delta: int = 0


class UISkillRollbackPlanner:
    def plan(self, current_version_id: str, target_version_id: str) -> RollbackPlan:
        if current_version_id == target_version_id:
            raise ValueError("Cannot roll back to the same version.")

        init_db()
        db = SessionLocal()
        try:
            current = get_ui_skill_version_record(db, current_version_id)
            target = get_ui_skill_version_record(db, target_version_id)

            if current is None:
                raise ValueError(f"Current version '{current_version_id}' not found.")
            if target is None:
                raise ValueError(f"Target version '{target_version_id}' not found.")
            if current.skill_id != target.skill_id:
                raise ValueError("Cannot roll back across different skill families.")

            blocking: list[str] = []
            warnings: list[str] = []

            if current.status not in ("active", "approved"):
                blocking.append(f"Current version status is '{current.status}' — can only roll back from 'active' or 'approved'.")
            if target.status in ("deprecated",):
                blocking.append(f"Target version status is '{target.status}' — cannot reactivate deprecated versions.")
            if target.version_number >= current.version_number:
                warnings.append(
                    f"Target v{target.version_number} is not older than current v{current.version_number}. "
                    "Consider promoting a newer version instead."
                )

            steps_current = len(json.loads(current.steps_json))
            steps_target = len(json.loads(target.steps_json))
            step_delta = steps_target - steps_current

            is_executable = len(blocking) == 0
            impact = (
                f"v{current.version_number} ({current.status}) → rolled_back; "
                f"v{target.version_number} ({target.status}) → active. "
                f"Step count change: {step_delta:+d}."
            )
            if not is_executable:
                impact = "Rollback blocked: " + "; ".join(blocking)

            return RollbackPlan(
                current_version_id=current_version_id,
                target_version_id=target_version_id,
                skill_id=current.skill_id,
                current_version_number=current.version_number,
                target_version_number=target.version_number,
                current_status=current.status,
                target_status=target.status,
                is_executable=is_executable,
                blocking_reasons=blocking,
                warnings=warnings,
                impact_summary=impact,
                step_delta=step_delta,
            )
        finally:
            db.close()
