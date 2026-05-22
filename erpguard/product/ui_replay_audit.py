from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_replay_run, list_ui_replay_step_audits
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class UIReplayStepAuditEntry:
    audit_id: str
    replay_run_id: str
    step_index: int
    step_id: str
    step_type: str
    status: str
    before_state: dict = field(default_factory=dict)
    after_state: dict = field(default_factory=dict)
    evidence: dict = field(default_factory=dict)
    error_text: str | None = None
    created_at: str = ""


@dataclass(frozen=True)
class UIReplayAuditResult:
    replay_id: str
    compiled_skill_id: str
    target_base_url: str
    replay_status: str
    step_count: int
    steps_passed: int
    steps_failed: int
    entries: list[UIReplayStepAuditEntry] = field(default_factory=list)


class UIReplayAuditService:
    def get_audit(self, replay_id: str) -> UIReplayAuditResult | None:
        init_db()
        db = SessionLocal()
        try:
            run = get_ui_replay_run(db, replay_id)
            if run is None:
                return None
            rows = list_ui_replay_step_audits(db, replay_id)
            entries = [
                UIReplayStepAuditEntry(
                    audit_id=r.id,
                    replay_run_id=r.replay_run_id,
                    step_index=r.step_index,
                    step_id=r.step_id,
                    step_type=r.step_type,
                    status=r.status,
                    before_state=json.loads(r.before_state_json) if r.before_state_json else {},
                    after_state=json.loads(r.after_state_json) if r.after_state_json else {},
                    evidence=json.loads(r.evidence_json) if r.evidence_json else {},
                    error_text=r.error_text,
                    created_at=r.created_at.isoformat(),
                )
                for r in rows
            ]
            return UIReplayAuditResult(
                replay_id=run.id,
                compiled_skill_id=run.compiled_skill_id,
                target_base_url=run.target_base_url,
                replay_status=run.status,
                step_count=run.step_count,
                steps_passed=run.steps_passed,
                steps_failed=run.steps_failed,
                entries=entries,
            )
        finally:
            db.close()
