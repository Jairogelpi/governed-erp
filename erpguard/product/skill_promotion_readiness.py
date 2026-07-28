from __future__ import annotations

import json
from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_ui_replay_run,
    get_ui_skill_version_record,
    list_ui_replay_failures,
    update_ui_skill_version_status,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class PromotionReadiness:
    version_id: str
    ready: bool
    readiness_level: str
    checks: list[dict] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class UISkillPromotionReadinessService:
    def compute(self, version_id: str) -> PromotionReadiness:
        init_db()
        db = SessionLocal()
        try:
            version = get_ui_skill_version_record(db, version_id)
            if version is None:
                raise ValueError(f"Skill version '{version_id}' not found.")

            checks: list[dict] = []
            blocking: list[str] = []
            warnings: list[str] = []

            # Check 1: already active or beyond
            if version.status in ("active", "deprecated", "rolled_back"):
                blocking.append(f"Version is already {version.status} — cannot promote further.")
            checks.append({"check": "lifecycle_status", "ok": version.status not in ("active", "deprecated", "rolled_back"), "value": version.status})

            # Check 2: has a replay run attached
            has_replay = bool(version.replay_run_id)
            if not has_replay:
                warnings.append("No verified replay attached. Promotion allowed but not recommended.")
            checks.append({"check": "has_replay_run", "ok": has_replay, "value": version.replay_run_id})

            # Check 3: replay passed (if present)
            replay_passed = True
            if version.replay_run_id:
                replay = get_ui_replay_run(db, version.replay_run_id)
                if replay:
                    replay_passed = replay.status in ("completed",)
                    if not replay_passed:
                        blocking.append(f"Linked replay status is '{replay.status}' (not 'completed').")
                    steps_total = replay.step_count or 1
                    pass_rate = round(replay.steps_passed / steps_total * 100, 1)
                    checks.append({"check": "replay_passed", "ok": replay_passed, "pass_rate_pct": pass_rate})

                    # Check 4: no critical failures
                    failures = list_ui_replay_failures(db, version.replay_run_id)
                    critical = [f for f in failures if f.severity == "critical"]
                    if critical:
                        blocking.append(f"{len(critical)} critical failure(s) in linked replay.")
                    checks.append({"check": "no_critical_failures", "ok": len(critical) == 0, "critical_count": len(critical)})
                else:
                    warnings.append("Linked replay_run_id not found in DB.")

            # Check 5: has steps
            has_steps = len(json.loads(version.steps_json)) > 0
            if not has_steps:
                blocking.append("Version has no compiled steps.")
            checks.append({"check": "has_steps", "ok": has_steps})

            # Check 6: no LLM at replay
            checks.append({"check": "no_llm_required", "ok": not version.llm_required})

            ready = len(blocking) == 0
            readiness_level = "ready" if ready else ("blocked" if blocking else "warning")

            readiness_json = json.dumps({
                "ready": ready, "readiness_level": readiness_level,
                "checks": checks, "blocking_reasons": blocking, "warnings": warnings,
            }, default=str)
            update_ui_skill_version_status(
                db, version_id, status=version.status,
                promotion_readiness_json=readiness_json,
            )

            return PromotionReadiness(
                version_id=version_id,
                ready=ready,
                readiness_level=readiness_level,
                checks=checks,
                blocking_reasons=blocking,
                warnings=warnings,
            )
        finally:
            db.close()
