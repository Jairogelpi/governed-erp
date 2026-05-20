from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_write_impact_preview,
    get_latest_write_impact_preview_for_skill,
    get_write_readiness_assessment,
)
from erpguard.product.models import WriteDetectedCandidateModel, WriteImpactPreviewModel


class WriteImpactPreviewService:
    def __init__(self, session) -> None:
        self.session = session

    def generate(self, assessment_id: str) -> WriteImpactPreviewModel:
        assessment_row = get_write_readiness_assessment(self.session, assessment_id)
        if assessment_row is None:
            raise ObjectNotFoundError(f"Assessment '{assessment_id}' not found.")

        candidates = [
            WriteDetectedCandidateModel.model_validate(c)
            for c in json.loads(assessment_row.write_candidates_json)
        ]

        affected_models = sorted({c.odoo_model for c in candidates})
        reversible = all(
            c.write_method in ("write", "action_cancel", "button_approve")
            for c in candidates
        ) if candidates else True

        estimated_count = len(candidates) * 10

        rollback_strategy = (
            "Restore affected records from pre-execution backup snapshot."
            if not reversible
            else "Revert field values using backup delta captured before execution."
        )

        row = create_write_impact_preview(
            session=self.session,
            assessment_id=assessment_id,
            skill_id=assessment_row.skill_id,
            impact_summary=f"{len(candidates)} write candidate(s) detected across {len(affected_models)} model(s). "
                           f"Estimated {estimated_count} records affected. No real writes executed — analysis only.",
            affected_models_json=json.dumps(affected_models),
            estimated_record_count=estimated_count,
            reversible=reversible,
            rollback_strategy=rollback_strategy,
        )

        return WriteImpactPreviewModel(
            impact_id=row.id,
            assessment_id=row.assessment_id,
            skill_id=row.skill_id,
            impact_summary=row.impact_summary,
            affected_models=json.loads(row.affected_models_json),
            estimated_record_count=row.estimated_record_count,
            reversible=row.reversible,
            rollback_strategy=row.rollback_strategy,
            can_execute_real_writes=False,
            created_at=row.created_at.isoformat(),
        )

    def get_latest(self, skill_id: str) -> WriteImpactPreviewModel | None:
        row = get_latest_write_impact_preview_for_skill(self.session, skill_id)
        if row is None:
            return None
        return WriteImpactPreviewModel(
            impact_id=row.id,
            assessment_id=row.assessment_id,
            skill_id=row.skill_id,
            impact_summary=row.impact_summary,
            affected_models=json.loads(row.affected_models_json),
            estimated_record_count=row.estimated_record_count,
            reversible=row.reversible,
            rollback_strategy=row.rollback_strategy,
            can_execute_real_writes=False,
            created_at=row.created_at.isoformat(),
        )
