from __future__ import annotations

import json

from erpguard.core.errors import ObjectNotFoundError
from erpguard.db.repositories import (
    create_r2_promotion_gate,
    get_r2_evidence_review_for_run,
    get_r2_execution_report_for_run,
    get_r2_promotion_gate_for_run,
    get_r2_rollback_rehearsal_for_run,
    get_r2_write_pilot_run,
)

_MAX_ALLOWED_RESIDUAL_RISK_SCORE = 30


class R2PromotionGateService:
    def __init__(self, session) -> None:
        self.session = session

    def evaluate(self, run_id: str) -> dict:
        existing = get_r2_promotion_gate_for_run(self.session, run_id)
        if existing:
            return self._to_dict(existing)

        run_row = get_r2_write_pilot_run(self.session, run_id)
        if run_row is None:
            raise ObjectNotFoundError(f"R2 write pilot run '{run_id}' not found.")

        review_row = get_r2_evidence_review_for_run(self.session, run_id)
        rehearsal_row = get_r2_rollback_rehearsal_for_run(self.session, run_id)
        report_row = get_r2_execution_report_for_run(self.session, run_id)

        checks, blocking_reasons = self._run_checks(run_row, review_row, rehearsal_row, report_row)

        blocked = len(blocking_reasons) > 0
        gate_status = "blocked" if blocked else "passed"

        row = create_r2_promotion_gate(
            self.session,
            run_id=run_id,
            skill_id=run_row.skill_id,
            gate_status=gate_status,
            blocked=blocked,
            checks_json=json.dumps(checks),
            blocking_reasons_json=json.dumps(blocking_reasons),
        )
        return self._to_dict(row)

    def _run_checks(self, run_row, review_row, rehearsal_row, report_row) -> tuple[list, list]:
        checks = []
        blocking_reasons = []

        def _check(name: str, passed: bool, description: str, blocking: bool = True):
            checks.append({"name": name, "passed": passed, "description": description})
            if not passed and blocking:
                blocking_reasons.append(f"{name}: {description}")

        _check(
            "run_completed_or_blocked",
            run_row.status in ("completed", "blocked"),
            "R2 pilot run must have a terminal status (completed or blocked).",
        )
        _check(
            "evidence_review_done",
            review_row is not None,
            "Evidence review (pre/post snapshot comparison) must be completed.",
        )
        _check(
            "no_drift_detected",
            review_row is None or not review_row.drift_detected,
            "No unexpected field drift detected between pre and post snapshots.",
        )
        _check(
            "rollback_rehearsal_done",
            rehearsal_row is not None,
            "Rollback rehearsal must be completed before promotion.",
        )
        _check(
            "rollback_rehearsal_passed",
            rehearsal_row is None or rehearsal_row.rehearsal_passed,
            "Rollback rehearsal must pass (instructions complete and valid).",
        )
        _check(
            "execution_report_generated",
            report_row is not None,
            "Execution report must be generated before promotion.",
        )
        _check(
            "residual_risk_acceptable",
            report_row is None or report_row.residual_risk_score <= _MAX_ALLOWED_RESIDUAL_RISK_SCORE,
            f"Residual risk score must be <= {_MAX_ALLOWED_RESIDUAL_RISK_SCORE}.",
        )
        _check(
            "generic_writes_locked",
            True,
            "ALLOW_GENERIC_REAL_ODOO_WRITES=false (permanent invariant).",
        )
        _check(
            "r3_r4_writes_locked",
            True,
            "ALLOW_R3_R4_REAL_WRITES=false (permanent invariant).",
        )

        return checks, blocking_reasons

    @staticmethod
    def _to_dict(row) -> dict:
        return {
            "gate_id": row.id,
            "run_id": row.run_id,
            "skill_id": row.skill_id,
            "gate_status": row.gate_status,
            "blocked": row.blocked,
            "checks": json.loads(row.checks_json),
            "blocking_reasons": json.loads(row.blocking_reasons_json),
            "safety_invariants": {
                "allow_generic_real_odoo_writes": False,
                "allow_r3_r4_real_writes": False,
                "can_execute_real_writes": False,
            },
            "created_at": row.created_at.isoformat(),
        }
