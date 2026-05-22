from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.product.ui_replay_audit import UIReplayAuditService


@dataclass(frozen=True)
class UIReplayReport:
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
    audit_evidence_count: int
    findings: list[str] = field(default_factory=list)
    summary: str = ""


class UIReplayReportService:
    _audit = UIReplayAuditService()

    def get_report(self, replay_id: str) -> UIReplayReport | None:
        audit = self._audit.get_audit(replay_id)
        if audit is None:
            return None

        total = audit.step_count or 1
        rate = round(audit.steps_passed / total * 100, 1)

        findings: list[str] = []
        for entry in audit.entries:
            if entry.status == "failed":
                findings.append(f"Step {entry.step_id} ({entry.step_type}) failed: {entry.error_text or 'unknown error'}")
            guard_finding = (entry.evidence or {}).get("finding")
            if guard_finding:
                findings.append(f"Guard {entry.step_id}: {guard_finding}")

        if audit.steps_failed == 0:
            summary = f"Replay completed successfully — all {audit.steps_passed} steps passed."
        else:
            summary = (
                f"Replay completed with {audit.steps_failed} failure(s). "
                f"{audit.steps_passed}/{audit.step_count} steps passed."
            )

        return UIReplayReport(
            replay_id=replay_id,
            compiled_skill_id=audit.compiled_skill_id,
            target_base_url=audit.target_base_url,
            replay_status=audit.replay_status,
            step_count=audit.step_count,
            steps_passed=audit.steps_passed,
            steps_failed=audit.steps_failed,
            success_rate_pct=rate,
            llm_used_at_replay=False,
            deterministic=True,
            audit_evidence_count=len(audit.entries),
            findings=findings,
            summary=summary,
        )
