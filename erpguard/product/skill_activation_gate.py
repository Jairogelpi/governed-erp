from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import get_active_ui_skill_version, get_ui_skill_version_record
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class ActivationGateResult:
    version_id: str
    can_activate: bool
    gate_status: str
    checks: list[dict] = field(default_factory=list)
    blocking_reasons: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


class UISkillActivationGateService:
    def check(self, version_id: str) -> ActivationGateResult:
        init_db()
        db = SessionLocal()
        try:
            version = get_ui_skill_version_record(db, version_id)
            if version is None:
                raise ValueError(f"Skill version '{version_id}' not found.")

            checks: list[dict] = []
            blocking: list[str] = []
            warnings: list[str] = []

            status_ok = version.status == "approved"
            if not status_ok:
                blocking.append(f"Version status is '{version.status}' — must be 'approved' to activate.")
            checks.append({"check": "status_is_approved", "ok": status_ok, "value": version.status})

            no_llm = not version.llm_required
            if not no_llm:
                blocking.append("Version requires LLM at replay time — activation blocked.")
            checks.append({"check": "no_llm_required", "ok": no_llm})

            runtime_ok = version.runtime_type == "deterministic_ui"
            if not runtime_ok:
                blocking.append(f"Runtime type '{version.runtime_type}' is not deterministic_ui.")
            checks.append({"check": "deterministic_runtime", "ok": runtime_ok})

            existing_active = get_active_ui_skill_version(db, version.skill_id)
            if existing_active and existing_active.id != version_id:
                warnings.append(
                    f"Skill '{version.skill_id}' already has an active version '{existing_active.id}'. "
                    "It must be deprecated first."
                )
            checks.append({"check": "no_conflicting_active", "ok": existing_active is None or existing_active.id == version_id})

            can_activate = len(blocking) == 0
            gate_status = "open" if can_activate else "blocked"

            return ActivationGateResult(
                version_id=version_id,
                can_activate=can_activate,
                gate_status=gate_status,
                checks=checks,
                blocking_reasons=blocking,
                warnings=warnings,
            )
        finally:
            db.close()
