from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.db.repositories import (
    add_ui_replay_failure,
    add_ui_replay_step_audit,
    add_ui_replay_verification,
    create_ui_replay_run,
    finish_ui_replay_run,
    get_ui_compiled_skill,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.ui_replay_runtime import UIReplayRuntime, _FAKE_ERP_MARKER
from erpguard.product.ui_replay_verifier import UIReplayVerifier

_base_runtime = UIReplayRuntime()
_verifier = UIReplayVerifier()


@dataclass(frozen=True)
class VerifiedStepResult:
    step_index: int
    step_id: str
    step_type: str
    status: str
    verification_status: str
    before_state: dict = field(default_factory=dict)
    after_state: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    checks: dict = field(default_factory=dict)
    failure_type: str | None = None
    recovery_suggestion: str = ""
    error: str | None = None


@dataclass(frozen=True)
class VerifiedReplayResult:
    replay_id: str
    compiled_skill_id: str
    status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    steps_verification_failed: int
    step_results: list[VerifiedStepResult] = field(default_factory=list)
    finished_at: str = ""


class UIVerifiedReplayRuntime:
    def replay(self, compiled_skill_id: str, target_base_url: str) -> VerifiedReplayResult:
        if _FAKE_ERP_MARKER not in target_base_url:
            raise ValueError(
                f"Verified replay is only permitted against Fake ERP targets. "
                f"Received: {target_base_url!r}"
            )

        init_db()
        db = SessionLocal()
        try:
            skill = get_ui_compiled_skill(db, compiled_skill_id)
            if skill is None:
                raise ValueError(f"Compiled skill '{compiled_skill_id}' not found.")

            steps = json.loads(skill.steps_json)
            run = create_ui_replay_run(
                db,
                compiled_skill_id=compiled_skill_id,
                target_base_url=target_base_url,
                step_count=len(steps),
            )

            step_results: list[VerifiedStepResult] = []
            erp_state: dict = {"current_url": target_base_url, "current_order": None}

            for idx, step in enumerate(steps):
                step_id = step.get("id", f"step_{idx}")
                step_type = step.get("type", "unknown")
                before = dict(erp_state)

                pre_verification = _verifier.verify_pre_step(step, idx, erp_state)

                if not pre_verification.all_pre_checks_ok():
                    add_ui_replay_verification(
                        db,
                        replay_run_id=run.id,
                        step_index=idx,
                        step_id=step_id,
                        page_state_ok=pre_verification.page_state_ok,
                        record_identity_ok=pre_verification.record_identity_ok,
                        selector_ambiguity_ok=pre_verification.selector_ambiguity_ok,
                        modal_error_ok=pre_verification.modal_error_ok,
                        post_state_ok=False,
                        overall_status="verification_failed",
                        checks_json=pre_verification.to_checks_json(),
                    )
                    if pre_verification.failure:
                        add_ui_replay_failure(
                            db,
                            replay_run_id=run.id,
                            step_index=idx,
                            step_id=step_id,
                            failure_type=pre_verification.failure.failure_type,
                            failure_detail=pre_verification.failure.detail,
                            recovery_suggestion=pre_verification.recovery_suggestion,
                            severity=pre_verification.failure.severity,
                        )
                    add_ui_replay_step_audit(
                        db,
                        replay_run_id=run.id,
                        step_index=idx,
                        step_id=step_id,
                        step_type=step_type,
                        status="verification_failed",
                        before_state_json=json.dumps(before, default=str),
                        after_state_json=json.dumps(before, default=str),
                        evidence_json=pre_verification.to_checks_json(),
                        error_text=pre_verification.failure.detail if pre_verification.failure else None,
                    )
                    step_results.append(VerifiedStepResult(
                        step_index=idx, step_id=step_id, step_type=step_type,
                        status="verification_failed",
                        verification_status="verification_failed",
                        before_state=before, after_state=before,
                        evidence={}, checks=pre_verification.checks,
                        failure_type=pre_verification.failure.failure_type if pre_verification.failure else None,
                        recovery_suggestion=pre_verification.recovery_suggestion,
                    ))
                    continue

                base_result = _base_runtime._execute_step(idx, step, erp_state)
                after = dict(erp_state)

                post_verification = _verifier.verify_post_step(pre_verification, step, before, after)

                add_ui_replay_verification(
                    db,
                    replay_run_id=run.id,
                    step_index=idx,
                    step_id=step_id,
                    page_state_ok=post_verification.page_state_ok,
                    record_identity_ok=post_verification.record_identity_ok,
                    selector_ambiguity_ok=post_verification.selector_ambiguity_ok,
                    modal_error_ok=post_verification.modal_error_ok,
                    post_state_ok=post_verification.post_state_ok,
                    overall_status=post_verification.overall_status,
                    checks_json=post_verification.to_checks_json(),
                )

                if post_verification.failure and post_verification.failure.failure_type != "no_failure":
                    add_ui_replay_failure(
                        db,
                        replay_run_id=run.id,
                        step_index=idx,
                        step_id=step_id,
                        failure_type=post_verification.failure.failure_type,
                        failure_detail=post_verification.failure.detail,
                        recovery_suggestion=post_verification.recovery_suggestion,
                        severity=post_verification.failure.severity,
                    )

                final_status = base_result.status if post_verification.post_state_ok else "verification_failed"
                add_ui_replay_step_audit(
                    db,
                    replay_run_id=run.id,
                    step_index=idx,
                    step_id=step_id,
                    step_type=step_type,
                    status=final_status,
                    before_state_json=json.dumps(base_result.before_state, default=str),
                    after_state_json=json.dumps(base_result.after_state, default=str),
                    evidence_json=json.dumps({**base_result.evidence, "verification": post_verification.checks}, default=str),
                    error_text=base_result.error,
                )
                step_results.append(VerifiedStepResult(
                    step_index=idx, step_id=step_id, step_type=step_type,
                    status=final_status,
                    verification_status=post_verification.overall_status,
                    before_state=base_result.before_state,
                    after_state=base_result.after_state,
                    evidence=base_result.evidence,
                    checks=post_verification.checks,
                    failure_type=post_verification.failure.failure_type if post_verification.failure else None,
                    recovery_suggestion=post_verification.recovery_suggestion,
                    error=base_result.error,
                ))

            passed = sum(1 for r in step_results if r.status == "passed")
            verif_failed = sum(1 for r in step_results if r.status == "verification_failed")
            failed = len(step_results) - passed - verif_failed

            if verif_failed > 0 or failed > 0:
                final_status = "completed_with_failures"
            else:
                final_status = "completed"

            finished_at = datetime.now(timezone.utc)
            finish_ui_replay_run(
                db, run.id,
                status=final_status,
                steps_passed=passed,
                steps_failed=failed + verif_failed,
                result_json=json.dumps({
                    "step_count": len(steps), "passed": passed,
                    "failed": failed, "verification_failed": verif_failed,
                }, default=str),
            )

            return VerifiedReplayResult(
                replay_id=run.id,
                compiled_skill_id=compiled_skill_id,
                status=final_status,
                step_count=len(steps),
                steps_passed=passed,
                steps_failed=failed + verif_failed,
                steps_verification_failed=verif_failed,
                step_results=step_results,
                finished_at=finished_at.isoformat(),
            )
        finally:
            db.close()
