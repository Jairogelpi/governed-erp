from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_write_readiness_assessment,
    get_latest_skill_version,
    get_write_readiness_assessment,
)
from erpguard.release_ops.models import (
    WritePermissionPreviewModel,
    WriteReadinessAssessmentModel,
)
from erpguard.release_ops.write_candidate_detector import WriteCandidateDetector
from erpguard.release_ops.write_permission_preview import WritePermissionPreviewService
from erpguard.release_ops.write_risk_matrix import WriteRiskMatrix


class WriteReadinessAssessmentService:
    def __init__(self, session) -> None:
        self.session = session

    def run(self, skill_id: str) -> WriteReadinessAssessmentModel:
        version_row = get_latest_skill_version(self.session, skill_id)
        if version_row is None:
            raise ObjectNotFoundError(f"Skill '{skill_id}' has no compiled version.")

        candidates = WriteCandidateDetector(self.session).detect(skill_id)
        risk_matrix_svc = WriteRiskMatrix()
        risk_entries = risk_matrix_svc.classify(candidates)
        overall_risk = risk_matrix_svc.overall_risk_level(risk_entries)
        blocking_issues = risk_matrix_svc.blocking_issues(risk_entries)
        can_certify = risk_matrix_svc.can_certify(risk_entries)

        permission_preview = WritePermissionPreviewService().compute(skill_id, candidates)

        row = create_write_readiness_assessment(
            session=self.session,
            skill_id=skill_id,
            skill_version_id=version_row.id,
            status="completed",
            write_candidates_json=json.dumps([c.model_dump() for c in candidates]),
            risk_matrix_json=json.dumps([e.model_dump() for e in risk_entries]),
            overall_risk_level=overall_risk,
            can_certify_write_readiness=can_certify,
            blocking_issues_json=json.dumps(blocking_issues),
            permission_preview_json=json.dumps(permission_preview.model_dump()),
        )

        return self._row_to_model(row, candidates=candidates, risk_entries=risk_entries,
                                  permission_preview=permission_preview, blocking_issues=blocking_issues)

    def get(self, assessment_id: str) -> WriteReadinessAssessmentModel:
        from erpguard.release_ops.models import WriteDetectedCandidateModel, WriteRiskMatrixEntryModel
        row = get_write_readiness_assessment(self.session, assessment_id)
        if row is None:
            raise ObjectNotFoundError(f"Assessment '{assessment_id}' not found.")
        candidates = [WriteDetectedCandidateModel.model_validate(c) for c in json.loads(row.write_candidates_json)]
        risk_entries = [WriteRiskMatrixEntryModel.model_validate(e) for e in json.loads(row.risk_matrix_json)]
        pp = WritePermissionPreviewModel.model_validate(json.loads(row.permission_preview_json))
        blocking = json.loads(row.blocking_issues_json)
        return self._row_to_model(row, candidates=candidates, risk_entries=risk_entries,
                                  permission_preview=pp, blocking_issues=blocking)

    @staticmethod
    def _row_to_model(row, *, candidates, risk_entries, permission_preview, blocking_issues) -> WriteReadinessAssessmentModel:
        return WriteReadinessAssessmentModel(
            assessment_id=row.id,
            skill_id=row.skill_id,
            skill_version_id=row.skill_version_id,
            status=row.status,
            write_candidates=candidates,
            risk_matrix=risk_entries,
            overall_risk_level=row.overall_risk_level,
            can_certify_write_readiness=row.can_certify_write_readiness,
            blocking_issues=blocking_issues,
            permission_preview=permission_preview,
            can_execute_real_writes=False,
            real_erp_writes_enabled=False,
            created_at=row.created_at.isoformat(),
        )
