from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.product.active_skill_run_history import ActiveSkillRunHistoryService
from erpguard.recording_pipeline.ui_robust_replay_report import UIRobustReplayReportService


@dataclass(frozen=True)
class ActiveSkillRunReport:
    run_id: str
    version_id: str
    skill_id: str
    run_status: str
    actor: str
    trigger: str
    target_base_url: str
    replay_run_id: str | None
    step_count: int
    steps_passed: int
    steps_failed: int
    steps_verification_failed: int
    success_rate_pct: float
    llm_used_at_replay: bool
    deterministic: bool
    failure_count: int
    failures: list[dict] = field(default_factory=list)
    verifications: list[dict] = field(default_factory=list)
    event_log: list[dict] = field(default_factory=list)
    recovery_actions_required: bool = False
    summary: str = ""
    created_at: str = ""
    finished_at: str = ""


class ActiveSkillRunReportService:
    _history = ActiveSkillRunHistoryService()
    _robust = UIRobustReplayReportService()

    def get_report(self, run_id: str) -> ActiveSkillRunReport | None:
        run = self._history.get_run(run_id)
        if run is None:
            return None

        events = self._history.list_run_events(run_id) or []
        event_log = [
            {
                "event_type": e.event_type,
                "status": e.status,
                "detail": e.detail,
                "created_at": e.created_at,
            }
            for e in events
        ]

        step_count = 0
        steps_passed = 0
        steps_failed = 0
        steps_verification_failed = 0
        success_rate = 0.0
        failures: list[dict] = []
        verifications: list[dict] = []
        recovery_required = False

        if run.replay_run_id:
            robust = self._robust.get_report(run.replay_run_id)
            if robust:
                step_count = robust.step_count
                steps_passed = robust.steps_passed
                steps_failed = robust.steps_failed
                success_rate = robust.success_rate_pct
                recovery_required = robust.recovery_actions_required
                failures = [
                    {
                        "step_index": f.step_index, "step_id": f.step_id,
                        "failure_type": f.failure_type, "failure_detail": f.failure_detail,
                        "recovery_suggestion": f.recovery_suggestion, "severity": f.severity,
                    }
                    for f in robust.failures
                ]
                verifications = [
                    {
                        "step_index": v.step_index, "step_id": v.step_id,
                        "page_state_ok": v.page_state_ok,
                        "record_identity_ok": v.record_identity_ok,
                        "selector_ambiguity_ok": v.selector_ambiguity_ok,
                        "modal_error_ok": v.modal_error_ok,
                        "post_state_ok": v.post_state_ok,
                        "overall_status": v.overall_status,
                    }
                    for v in robust.verifications
                ]
                steps_verification_failed = sum(1 for v in robust.verifications if v.overall_status == "verification_failed")

        return ActiveSkillRunReport(
            run_id=run_id,
            version_id=run.version_id,
            skill_id=run.skill_id,
            run_status=run.status,
            actor=run.actor,
            trigger=run.trigger,
            target_base_url=run.target_base_url,
            replay_run_id=run.replay_run_id,
            step_count=step_count,
            steps_passed=steps_passed,
            steps_failed=steps_failed,
            steps_verification_failed=steps_verification_failed,
            success_rate_pct=success_rate,
            llm_used_at_replay=False,
            deterministic=True,
            failure_count=len(failures),
            failures=failures,
            verifications=verifications,
            event_log=event_log,
            recovery_actions_required=recovery_required,
            summary=run.summary.get("summary", "") if isinstance(run.summary, dict) else "",
            created_at=run.created_at,
            finished_at=run.finished_at,
        )
