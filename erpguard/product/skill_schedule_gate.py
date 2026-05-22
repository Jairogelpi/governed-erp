from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db

_FAKE_ERP_MARKER = "/fake-erp"
_MIN_INTERVAL_FLOOR = 60
_MIN_DEDUP_WINDOW = 5


@dataclass(frozen=True)
class ScheduleGateResult:
    version_id: str
    can_schedule: bool
    gate_status: str
    checks: list[dict] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)


class SkillScheduleGateService:
    def check(
        self,
        version_id: str,
        target_base_url: str,
        interval_seconds: int,
        min_interval_seconds: int,
        dedup_window_seconds: int,
    ) -> ScheduleGateResult:
        init_db()
        db = SessionLocal()
        try:
            version = get_ui_skill_version_record(db, version_id)
            if version is None:
                raise ValueError(f"Skill version '{version_id}' not found.")

            checks: list[dict] = []
            blocking: list[str] = []

            status_ok = version.status == "active"
            if not status_ok:
                blocking.append(f"Version status is '{version.status}' — only 'active' versions can be scheduled.")
            checks.append({"check": "status_is_active", "ok": status_ok, "value": version.status})

            is_active_flag = version.is_active is True
            if not is_active_flag:
                blocking.append("Version is_active flag is False — must be currently active.")
            checks.append({"check": "is_active_flag", "ok": is_active_flag})

            no_llm = not version.llm_required
            if not no_llm:
                blocking.append("Version requires LLM at replay time — scheduling blocked.")
            checks.append({"check": "no_llm_required", "ok": no_llm})

            runtime_ok = version.runtime_type == "deterministic_ui"
            if not runtime_ok:
                blocking.append(f"Runtime type '{version.runtime_type}' is not deterministic_ui.")
            checks.append({"check": "deterministic_runtime", "ok": runtime_ok})

            target_ok = _FAKE_ERP_MARKER in target_base_url
            if not target_ok:
                blocking.append(f"Target URL '{target_base_url}' is not on Fake ERP. Production targets not permitted.")
            checks.append({"check": "target_is_fake_erp", "ok": target_ok})

            interval_ok = interval_seconds >= _MIN_INTERVAL_FLOOR
            if not interval_ok:
                blocking.append(f"interval_seconds={interval_seconds} below minimum floor {_MIN_INTERVAL_FLOOR}.")
            checks.append({"check": "interval_seconds_ge_min_floor", "ok": interval_ok, "value": interval_seconds})

            min_iv_ok = min_interval_seconds >= _MIN_INTERVAL_FLOOR
            if not min_iv_ok:
                blocking.append(f"min_interval_seconds={min_interval_seconds} below floor {_MIN_INTERVAL_FLOOR}.")
            checks.append({"check": "min_interval_seconds_ge_floor", "ok": min_iv_ok, "value": min_interval_seconds})

            interval_consistent = interval_seconds >= min_interval_seconds
            if not interval_consistent:
                blocking.append(f"interval_seconds={interval_seconds} is below min_interval_seconds={min_interval_seconds}.")
            checks.append({"check": "interval_ge_min_interval", "ok": interval_consistent})

            dedup_ok = dedup_window_seconds >= _MIN_DEDUP_WINDOW
            if not dedup_ok:
                blocking.append(f"dedup_window_seconds={dedup_window_seconds} below floor {_MIN_DEDUP_WINDOW}.")
            checks.append({"check": "dedup_window_ge_floor", "ok": dedup_ok})

            can_schedule = len(blocking) == 0
            return ScheduleGateResult(
                version_id=version_id,
                can_schedule=can_schedule,
                gate_status="open" if can_schedule else "blocked",
                checks=checks,
                blocking_reasons=blocking,
            )
        finally:
            db.close()
