from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db

_FAKE_ERP_MARKER = "/fake-erp"


@dataclass(frozen=True)
class RunGateResult:
    version_id: str
    can_run: bool
    gate_status: str
    checks: list[dict] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)


class ActiveSkillRunGateService:
    def check(self, version_id: str, target_base_url: str) -> RunGateResult:
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
                blocking.append(f"Version status is '{version.status}' — only 'active' versions can run.")
            checks.append({"check": "status_is_active", "ok": status_ok, "value": version.status})

            is_active_flag = version.is_active is True
            if not is_active_flag:
                blocking.append("Version is_active flag is False — must be the currently active version.")
            checks.append({"check": "is_active_flag", "ok": is_active_flag})

            no_llm = not version.llm_required
            if not no_llm:
                blocking.append("Version requires LLM at replay time — runner blocked.")
            checks.append({"check": "no_llm_required", "ok": no_llm})

            runtime_ok = version.runtime_type == "deterministic_ui"
            if not runtime_ok:
                blocking.append(f"Runtime type '{version.runtime_type}' is not deterministic_ui.")
            checks.append({"check": "deterministic_runtime", "ok": runtime_ok})

            target_ok = _FAKE_ERP_MARKER in target_base_url
            if not target_ok:
                blocking.append(f"Target URL '{target_base_url}' is not on Fake ERP. Production targets not permitted.")
            checks.append({"check": "target_is_fake_erp", "ok": target_ok, "value": target_base_url})

            can_run = len(blocking) == 0
            gate_status = "open" if can_run else "blocked"

            return RunGateResult(
                version_id=version_id,
                can_run=can_run,
                gate_status=gate_status,
                checks=checks,
                blocking_reasons=blocking,
            )
        finally:
            db.close()
