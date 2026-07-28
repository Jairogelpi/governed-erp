from __future__ import annotations

from dataclasses import dataclass

from erpguard.db.repositories import (
    create_ui_skill_version_lifecycle_event,
    get_ui_skill_version_record,
    update_ui_skill_version_status,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.skill_rollback_planner import UISkillRollbackPlanner

_planner = UISkillRollbackPlanner()


@dataclass(frozen=True)
class RollbackResult:
    skill_id: str
    rolled_back_version_id: str
    rolled_back_version_number: int
    reactivated_version_id: str
    reactivated_version_number: int
    actor: str
    reason: str


class UISkillRollbackService:
    def execute(
        self,
        current_version_id: str,
        target_version_id: str,
        actor: str = "system",
        reason: str = "",
    ) -> RollbackResult:
        plan = _planner.plan(current_version_id, target_version_id)
        if not plan.is_executable:
            raise ValueError(
                "Rollback plan is not executable: " + "; ".join(plan.blocking_reasons)
            )

        init_db()
        db = SessionLocal()
        try:
            current = get_ui_skill_version_record(db, current_version_id)
            target = get_ui_skill_version_record(db, target_version_id)
            assert current is not None and target is not None  # plan.is_executable already verified both exist

            update_ui_skill_version_status(db, current_version_id, status="rolled_back", is_active=False)
            create_ui_skill_version_lifecycle_event(
                db,
                version_id=current_version_id,
                skill_id=current.skill_id,
                event_type="rolled_back",
                from_status=current.status,
                to_status="rolled_back",
                actor=actor,
                reason=reason,
            )

            update_ui_skill_version_status(db, target_version_id, status="active", is_active=True)
            create_ui_skill_version_lifecycle_event(
                db,
                version_id=target_version_id,
                skill_id=target.skill_id,
                event_type="reactivated_via_rollback",
                from_status=target.status,
                to_status="active",
                actor=actor,
                reason=f"rollback_from_{current_version_id}",
            )

            return RollbackResult(
                skill_id=current.skill_id,
                rolled_back_version_id=current_version_id,
                rolled_back_version_number=current.version_number,
                reactivated_version_id=target_version_id,
                reactivated_version_number=target.version_number,
                actor=actor,
                reason=reason,
            )
        finally:
            db.close()
