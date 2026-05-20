from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_write_rollback_plan,
    get_latest_write_rollback_plan_for_skill,
    get_write_readiness_assessment,
)
from erpguard.product.models import WriteDetectedCandidateModel, WriteRollbackPlanModel


class WriteRollbackPlanService:
    def __init__(self, session) -> None:
        self.session = session

    def draft(self, assessment_id: str) -> WriteRollbackPlanModel:
        assessment_row = get_write_readiness_assessment(self.session, assessment_id)
        if assessment_row is None:
            raise ObjectNotFoundError(f"Assessment '{assessment_id}' not found.")

        candidates = [
            WriteDetectedCandidateModel.model_validate(c)
            for c in json.loads(assessment_row.write_candidates_json)
        ]

        rollback_steps = [
            "1. Capture pre-execution snapshot of all affected models via read-only export.",
            "2. Record all write candidate target IDs before execution.",
            "3. On rollback trigger: halt all in-flight write operations.",
            "4. Restore affected records from snapshot using Odoo import or reverse write.",
            "5. Verify data integrity with post-rollback read-only audit.",
            "6. Log rollback evidence with timestamps and operator identity.",
        ]

        for c in candidates:
            if c.write_method in ("unlink", "action_confirm", "button_validate", "action_done"):
                rollback_steps.append(
                    f"7. For {c.write_method} on {c.odoo_model}: manual restoration may be required — contact ERP administrator."
                )
                break

        backup_strategy = (
            "Automated JSON export of affected records pre-execution, stored in ERPGuard evidence store."
        )

        row = create_write_rollback_plan(
            session=self.session,
            assessment_id=assessment_id,
            skill_id=assessment_row.skill_id,
            rollback_steps_json=json.dumps(rollback_steps),
            backup_strategy=backup_strategy,
            estimated_rollback_time_minutes=30,
        )

        return WriteRollbackPlanModel(
            plan_id=row.id,
            assessment_id=row.assessment_id,
            skill_id=row.skill_id,
            rollback_steps=json.loads(row.rollback_steps_json),
            backup_strategy=row.backup_strategy,
            estimated_rollback_time_minutes=row.estimated_rollback_time_minutes,
            can_execute_real_writes=False,
            created_at=row.created_at.isoformat(),
        )

    def get_latest(self, skill_id: str) -> WriteRollbackPlanModel | None:
        row = get_latest_write_rollback_plan_for_skill(self.session, skill_id)
        if row is None:
            return None
        return WriteRollbackPlanModel(
            plan_id=row.id,
            assessment_id=row.assessment_id,
            skill_id=row.skill_id,
            rollback_steps=json.loads(row.rollback_steps_json),
            backup_strategy=row.backup_strategy,
            estimated_rollback_time_minutes=row.estimated_rollback_time_minutes,
            can_execute_real_writes=False,
            created_at=row.created_at.isoformat(),
        )
