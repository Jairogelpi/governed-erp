from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from erpguard.db.repositories import (
    add_active_skill_run_event,
    create_active_skill_run,
    get_ui_skill_version_record,
    update_active_skill_run,
)
from erpguard.db.session import SessionLocal, init_db
from erpguard.product.active_skill_input_validator import ActiveSkillInputValidatorService
from erpguard.product.active_skill_run_gate import ActiveSkillRunGateService
from erpguard.product.ui_verified_replay_runtime import UIVerifiedReplayRuntime


@dataclass(frozen=True)
class ActiveSkillRunResult:
    run_id: str
    version_id: str
    skill_id: str
    status: str
    replay_run_id: str | None
    steps_passed: int
    steps_failed: int
    steps_verification_failed: int
    summary: str
    actor: str
    target_base_url: str
    inputs: dict = field(default_factory=dict)
    gate_checks: list[dict] = field(default_factory=list)
    input_validation_checks: list[dict] = field(default_factory=list)
    finished_at: str = ""


class ActiveSkillRunnerService:
    _gate = ActiveSkillRunGateService()
    _validator = ActiveSkillInputValidatorService()
    _replay = UIVerifiedReplayRuntime()

    def run(
        self,
        version_id: str,
        target_base_url: str,
        actor: str = "manual_operator",
        inputs: dict | None = None,
    ) -> ActiveSkillRunResult:
        init_db()
        db = SessionLocal()
        try:
            version = get_ui_skill_version_record(db, version_id)
            if version is None:
                raise ValueError(f"Skill version '{version_id}' not found.")

            validation = self._validator.validate(target_base_url, inputs)
            gate = self._gate.check(version_id, target_base_url)

            run = create_active_skill_run(
                db,
                version_id=version_id,
                skill_id=version.skill_id,
                actor=actor,
                target_base_url=target_base_url,
                inputs_json=json.dumps(validation.sanitized_inputs, default=str),
                gate_result_json=json.dumps({"can_run": gate.can_run, "checks": gate.checks, "blocking_reasons": gate.blocking_reasons}, default=str),
                input_validation_json=json.dumps({"ok": validation.ok, "checks": validation.checks, "rejection_reasons": validation.rejection_reasons}, default=str),
            )

            add_active_skill_run_event(
                db, run_id=run.id, event_type="requested", status="info",
                detail=f"Manual run requested by {actor}",
                payload_json=json.dumps({"target_base_url": target_base_url}, default=str),
            )

            if not validation.ok:
                add_active_skill_run_event(
                    db, run_id=run.id, event_type="input_validation_failed", status="error",
                    detail="; ".join(validation.rejection_reasons),
                    payload_json=json.dumps({"checks": validation.checks, "rejection_reasons": validation.rejection_reasons}, default=str),
                )
                update_active_skill_run(
                    db, run.id, status="rejected",
                    summary_json=json.dumps({"reason": "input_validation_failed", "rejections": validation.rejection_reasons}, default=str),
                    finished_at=datetime.now(timezone.utc),
                )
                return self._build_result(run.id, version, "rejected", None, 0, 0, 0,
                                          "Input validation failed: " + "; ".join(validation.rejection_reasons),
                                          actor, target_base_url, validation.sanitized_inputs,
                                          gate.checks, validation.checks)

            add_active_skill_run_event(
                db, run_id=run.id, event_type="input_validated", status="ok",
                detail=f"{len(validation.sanitized_inputs)} input(s) accepted",
                payload_json=json.dumps(validation.sanitized_inputs, default=str),
            )

            if not gate.can_run:
                add_active_skill_run_event(
                    db, run_id=run.id, event_type="gate_blocked", status="error",
                    detail="; ".join(gate.blocking_reasons),
                    payload_json=json.dumps({"checks": gate.checks, "blocking_reasons": gate.blocking_reasons}, default=str),
                )
                update_active_skill_run(
                    db, run.id, status="blocked",
                    summary_json=json.dumps({"reason": "gate_blocked", "blocking_reasons": gate.blocking_reasons}, default=str),
                    finished_at=datetime.now(timezone.utc),
                )
                return self._build_result(run.id, version, "blocked", None, 0, 0, 0,
                                          "Gate blocked: " + "; ".join(gate.blocking_reasons),
                                          actor, target_base_url, validation.sanitized_inputs,
                                          gate.checks, validation.checks)

            add_active_skill_run_event(
                db, run_id=run.id, event_type="gate_passed", status="ok",
                detail="All gate checks passed",
                payload_json=json.dumps({"checks": gate.checks}, default=str),
            )

            add_active_skill_run_event(
                db, run_id=run.id, event_type="replay_started", status="info",
                detail=f"Verified replay against {target_base_url}",
            )

            try:
                replay = self._replay.replay(version.compiled_skill_id, target_base_url)
            except ValueError as exc:
                add_active_skill_run_event(
                    db, run_id=run.id, event_type="replay_error", status="error",
                    detail=str(exc),
                )
                update_active_skill_run(
                    db, run.id, status="error",
                    summary_json=json.dumps({"error": str(exc)}, default=str),
                    finished_at=datetime.now(timezone.utc),
                )
                return self._build_result(run.id, version, "error", None, 0, 0, 0,
                                          f"Replay error: {exc}",
                                          actor, target_base_url, validation.sanitized_inputs,
                                          gate.checks, validation.checks)

            final_status = "completed" if replay.steps_failed == 0 else "completed_with_failures"
            summary = (
                f"Run {final_status}: {replay.steps_passed}/{replay.step_count} step(s) passed. "
                f"Verification failures: {replay.steps_verification_failed}."
            )

            update_active_skill_run(
                db, run.id, status=final_status,
                replay_run_id=replay.replay_id,
                summary_json=json.dumps({
                    "replay_run_id": replay.replay_id,
                    "step_count": replay.step_count,
                    "steps_passed": replay.steps_passed,
                    "steps_failed": replay.steps_failed,
                    "steps_verification_failed": replay.steps_verification_failed,
                    "summary": summary,
                }, default=str),
                finished_at=datetime.now(timezone.utc),
            )

            add_active_skill_run_event(
                db, run_id=run.id, event_type="replay_finished", status="ok" if replay.steps_failed == 0 else "warning",
                detail=summary,
                payload_json=json.dumps({"replay_run_id": replay.replay_id}, default=str),
            )

            return self._build_result(run.id, version, final_status, replay.replay_id,
                                      replay.steps_passed, replay.steps_failed,
                                      replay.steps_verification_failed, summary,
                                      actor, target_base_url, validation.sanitized_inputs,
                                      gate.checks, validation.checks)
        finally:
            db.close()

    def _build_result(self, run_id, version, status, replay_run_id, passed, failed, vf,
                      summary, actor, target_base_url, inputs, gate_checks, val_checks) -> ActiveSkillRunResult:
        return ActiveSkillRunResult(
            run_id=run_id,
            version_id=version.id,
            skill_id=version.skill_id,
            status=status,
            replay_run_id=replay_run_id,
            steps_passed=passed,
            steps_failed=failed,
            steps_verification_failed=vf,
            summary=summary,
            actor=actor,
            target_base_url=target_base_url,
            inputs=inputs,
            gate_checks=gate_checks,
            input_validation_checks=val_checks,
            finished_at=datetime.now(timezone.utc).isoformat(),
        )
