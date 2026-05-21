from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_r2_execution_report,
    get_r2_evidence_review_for_run,
    get_r2_execution_report_for_run,
    get_r2_rollback_rehearsal_for_run,
    get_r2_write_pilot_run,
    list_r2_write_pilot_evidence_for_run,
)


def _compute_residual_risk(run_row, review_row, rehearsal_row) -> tuple[int, str]:
    score = 0
    if run_row.status == "blocked":
        return 0, "none"
    if run_row.status == "completed":
        score += 20
    if review_row and review_row.drift_detected:
        score += 40
    if rehearsal_row and not rehearsal_row.rehearsal_passed:
        score += 30
    if run_row.allow_r2_real_write_pilot:
        score += 10
    if score == 0:
        level = "none"
    elif score <= 20:
        level = "low"
    elif score <= 50:
        level = "medium"
    else:
        level = "high"
    return score, level


class R2ExecutionReportService:
    def __init__(self, session) -> None:
        self.session = session

    def get_or_generate(self, run_id: str) -> dict:
        existing = get_r2_execution_report_for_run(self.session, run_id)
        if existing:
            return self._to_dict(existing)

        run_row = get_r2_write_pilot_run(self.session, run_id)
        if run_row is None:
            raise ObjectNotFoundError(f"R2 write pilot run '{run_id}' not found.")

        evidence_rows = list_r2_write_pilot_evidence_for_run(self.session, run_id)
        review_row = get_r2_evidence_review_for_run(self.session, run_id)
        rehearsal_row = get_r2_rollback_rehearsal_for_run(self.session, run_id)

        residual_risk_score, risk_level = _compute_residual_risk(run_row, review_row, rehearsal_row)

        report = {
            "run_id": run_id,
            "skill_id": run_row.skill_id,
            "status": run_row.status,
            "executed_action": run_row.executed_action,
            "pre_snapshot": json.loads(run_row.pre_snapshot_json),
            "post_snapshot": json.loads(run_row.post_snapshot_json),
            "evidence_count": len(evidence_rows),
            "evidence_review": {
                "completed": review_row is not None,
                "fields_changed": review_row.fields_changed if review_row else None,
                "drift_detected": review_row.drift_detected if review_row else None,
            },
            "rollback_rehearsal": {
                "completed": rehearsal_row is not None,
                "rehearsal_passed": rehearsal_row.rehearsal_passed if rehearsal_row else None,
            },
            "residual_risk_score": residual_risk_score,
            "risk_level": risk_level,
            "safety_invariants": {
                "allow_r2_real_write_pilot": run_row.allow_r2_real_write_pilot,
                "allow_generic_real_odoo_writes": False,
                "allow_r3_r4_real_writes": False,
                "can_execute_real_writes": run_row.allow_r2_real_write_pilot,
            },
            "audit_notes": [
                "R2 write pilot — res.partner fields only",
                "Staging/demo environment enforced",
                "Double approval required",
                "Pre/post snapshots captured",
                "Rollback instructions stored",
                "ALLOW_GENERIC_REAL_ODOO_WRITES=false",
                "ALLOW_R3_R4_REAL_WRITES=false",
            ],
        }

        row = create_r2_execution_report(
            self.session,
            run_id=run_id,
            skill_id=run_row.skill_id,
            report_json=json.dumps(report),
            residual_risk_score=residual_risk_score,
            risk_level=risk_level,
            status="completed",
        )
        return self._to_dict(row)

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "report_id": row.id,
            "run_id": row.run_id,
            "skill_id": row.skill_id,
            "report": json.loads(row.report_json),
            "residual_risk_score": row.residual_risk_score,
            "risk_level": row.risk_level,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
