from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_write_readiness_certification,
    get_latest_write_impact_preview_for_skill,
    get_latest_write_readiness_assessment_for_skill,
    get_latest_write_readiness_certification_for_skill,
    get_latest_write_rollback_plan_for_skill,
    get_write_readiness_certification,
)
from erpguard.product.models import (
    WriteReadinessCertificationModel,
    WriteReadinessSummaryModel,
)


class WriteReadinessCertificationService:
    def __init__(self, session) -> None:
        self.session = session

    def certify(self, skill_id: str) -> WriteReadinessCertificationModel:
        assessment_row = get_latest_write_readiness_assessment_for_skill(self.session, skill_id)
        if assessment_row is None:
            raise ObjectNotFoundError(f"No write readiness assessment found for skill '{skill_id}'. Run assessment first.")

        impact_row = get_latest_write_impact_preview_for_skill(self.session, skill_id)
        if impact_row is None:
            raise ObjectNotFoundError(f"No write impact preview found for skill '{skill_id}'. Generate impact preview first.")

        rollback_row = get_latest_write_rollback_plan_for_skill(self.session, skill_id)
        if rollback_row is None:
            raise ObjectNotFoundError(f"No write rollback plan found for skill '{skill_id}'. Draft rollback plan first.")

        risk_level = assessment_row.overall_risk_level
        can_certify = assessment_row.can_certify_write_readiness

        if can_certify and risk_level in ("R1", "R2"):
            cert_status = "certified_read_only"
        else:
            cert_status = "blocked_high_risk"

        evidence = {
            "assessment_id": assessment_row.id,
            "impact_preview_id": impact_row.id,
            "rollback_plan_id": rollback_row.id,
            "overall_risk_level": risk_level,
            "can_certify_write_readiness": can_certify,
            "certification_status": cert_status,
            "ALLOW_REAL_ODOO_WRITES": False,
            "can_execute_real_writes": False,
            "approved_for_real_execution": False,
            "message": "Write capability readiness certified for analysis only. Real Odoo writes remain blocked.",
        }

        row = create_write_readiness_certification(
            session=self.session,
            skill_id=skill_id,
            assessment_id=assessment_row.id,
            certification_status=cert_status,
            overall_risk_level=risk_level,
            evidence_json=json.dumps(evidence),
            impact_preview_id=impact_row.id,
            rollback_plan_id=rollback_row.id,
        )

        return self._row_to_model(row)

    def get(self, certification_id: str) -> WriteReadinessCertificationModel:
        row = get_write_readiness_certification(self.session, certification_id)
        if row is None:
            raise ObjectNotFoundError(f"Certification '{certification_id}' not found.")
        return self._row_to_model(row)

    def get_latest(self, skill_id: str) -> WriteReadinessCertificationModel | None:
        row = get_latest_write_readiness_certification_for_skill(self.session, skill_id)
        if row is None:
            return None
        return self._row_to_model(row)

    def summary(self, skill_id: str) -> WriteReadinessSummaryModel:
        assessment_row = get_latest_write_readiness_assessment_for_skill(self.session, skill_id)
        impact_row = get_latest_write_impact_preview_for_skill(self.session, skill_id)
        rollback_row = get_latest_write_rollback_plan_for_skill(self.session, skill_id)
        cert_row = get_latest_write_readiness_certification_for_skill(self.session, skill_id)

        return WriteReadinessSummaryModel(
            skill_id=skill_id,
            has_assessment=assessment_row is not None,
            has_impact_preview=impact_row is not None,
            has_rollback_plan=rollback_row is not None,
            has_certification=cert_row is not None,
            overall_risk_level=assessment_row.overall_risk_level if assessment_row else None,
            certification_status=cert_row.certification_status if cert_row else None,
            can_certify_real_execution=False,
            can_execute_real_writes=False,
            real_erp_writes_enabled=False,
            approved_for_real_execution=False,
        )

    @staticmethod
    def _row_to_model(row) -> WriteReadinessCertificationModel:
        return WriteReadinessCertificationModel(
            certification_id=row.id,
            skill_id=row.skill_id,
            assessment_id=row.assessment_id,
            impact_preview_id=row.impact_preview_id,
            rollback_plan_id=row.rollback_plan_id,
            certification_status=row.certification_status,
            overall_risk_level=row.overall_risk_level,
            dual_approval_required=row.dual_approval_required,
            can_certify_real_execution=False,
            can_execute_real_writes=False,
            real_erp_writes_enabled=False,
            approved_for_real_execution=False,
            evidence=json.loads(row.evidence_json),
            created_at=row.created_at.isoformat(),
        )
