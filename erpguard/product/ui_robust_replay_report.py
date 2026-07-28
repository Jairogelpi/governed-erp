from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_ui_replay_run,
    list_ui_replay_verifications,
    list_ui_replay_failures,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class VerificationEntry:
    step_index: int
    step_id: str
    page_state_ok: bool
    record_identity_ok: bool
    selector_ambiguity_ok: bool
    modal_error_ok: bool
    post_state_ok: bool
    overall_status: str
    checks: dict = field(default_factory=dict)


@dataclass(frozen=True)
class FailureEntry:
    step_index: int
    step_id: str
    failure_type: str
    failure_detail: str
    recovery_suggestion: str
    severity: str


@dataclass(frozen=True)
class UIRobustReplayReport:
    replay_id: str
    compiled_skill_id: str
    target_base_url: str
    replay_status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    success_rate_pct: float
    llm_used_at_replay: bool
    deterministic: bool
    verification_count: int
    failure_count: int
    verifications: list[VerificationEntry] = field(default_factory=list)
    failures: list[FailureEntry] = field(default_factory=list)
    summary: str = ""
    recovery_actions_required: bool = False


class UIRobustReplayReportService:
    def get_report(self, replay_id: str) -> UIRobustReplayReport | None:
        init_db()
        db = SessionLocal()
        try:
            run = get_ui_replay_run(db, replay_id)
            if run is None:
                return None

            verif_rows = list_ui_replay_verifications(db, replay_id)
            failure_rows = list_ui_replay_failures(db, replay_id)

            verifications = [
                VerificationEntry(
                    step_index=r.step_index,
                    step_id=r.step_id,
                    page_state_ok=r.page_state_ok,
                    record_identity_ok=r.record_identity_ok,
                    selector_ambiguity_ok=r.selector_ambiguity_ok,
                    modal_error_ok=r.modal_error_ok,
                    post_state_ok=r.post_state_ok,
                    overall_status=r.overall_status,
                    checks=json.loads(r.checks_json) if r.checks_json else {},
                )
                for r in verif_rows
            ]

            failures = [
                FailureEntry(
                    step_index=r.step_index,
                    step_id=r.step_id,
                    failure_type=r.failure_type,
                    failure_detail=r.failure_detail,
                    recovery_suggestion=r.recovery_suggestion,
                    severity=r.severity,
                )
                for r in failure_rows
            ]

            total = run.step_count or 1
            rate = round(run.steps_passed / total * 100, 1)
            recovery_needed = len(failures) > 0

            if run.steps_failed == 0:
                summary = f"Verified replay completed — all {run.steps_passed} steps passed verification."
            else:
                critical = [f for f in failures if f.severity == "critical"]
                errors = [f for f in failures if f.severity == "error"]
                summary = (
                    f"Verified replay completed with {run.steps_failed} failure(s). "
                    f"{run.steps_passed}/{run.step_count} steps passed. "
                )
                if critical:
                    summary += f"{len(critical)} critical failure(s) require immediate attention."
                elif errors:
                    summary += f"{len(errors)} error(s) have non-executable recovery suggestions."

            return UIRobustReplayReport(
                replay_id=replay_id,
                compiled_skill_id=run.compiled_skill_id,
                target_base_url=run.target_base_url,
                replay_status=run.status,
                step_count=run.step_count,
                steps_passed=run.steps_passed,
                steps_failed=run.steps_failed,
                success_rate_pct=rate,
                llm_used_at_replay=False,
                deterministic=True,
                verification_count=len(verifications),
                failure_count=len(failures),
                verifications=verifications,
                failures=failures,
                summary=summary,
                recovery_actions_required=recovery_needed,
            )
        finally:
            db.close()

    def get_failures(self, replay_id: str) -> list[FailureEntry] | None:
        init_db()
        db = SessionLocal()
        try:
            run = get_ui_replay_run(db, replay_id)
            if run is None:
                return None
            rows = list_ui_replay_failures(db, replay_id)
            return [
                FailureEntry(
                    step_index=r.step_index,
                    step_id=r.step_id,
                    failure_type=r.failure_type,
                    failure_detail=r.failure_detail,
                    recovery_suggestion=r.recovery_suggestion,
                    severity=r.severity,
                )
                for r in rows
            ]
        finally:
            db.close()

    def get_verifications(self, replay_id: str) -> list[VerificationEntry] | None:
        init_db()
        db = SessionLocal()
        try:
            run = get_ui_replay_run(db, replay_id)
            if run is None:
                return None
            rows = list_ui_replay_verifications(db, replay_id)
            return [
                VerificationEntry(
                    step_index=r.step_index,
                    step_id=r.step_id,
                    page_state_ok=r.page_state_ok,
                    record_identity_ok=r.record_identity_ok,
                    selector_ambiguity_ok=r.selector_ambiguity_ok,
                    modal_error_ok=r.modal_error_ok,
                    post_state_ok=r.post_state_ok,
                    overall_status=r.overall_status,
                    checks=json.loads(r.checks_json) if r.checks_json else {},
                )
                for r in rows
            ]
        finally:
            db.close()
