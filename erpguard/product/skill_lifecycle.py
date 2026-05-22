from __future__ import annotations

from dataclasses import dataclass

from erpguard.db.repositories import (
    create_ui_skill_version_lifecycle_event,
    get_active_ui_skill_version,
    get_ui_skill_version_record,
    update_ui_skill_version_status,
)
from erpguard.db.session import SessionLocal, init_db

_VALID_TRANSITIONS: dict[str, set[str]] = {
    "draft":       {"candidate"},
    "candidate":   {"approved", "deprecated"},
    "validated":   {"approved", "deprecated"},
    "approved":    {"active", "deprecated"},
    "active":      {"deprecated", "rolled_back"},
    "deprecated":  set(),
    "rolled_back": set(),
}

_EVENT_NAMES: dict[tuple[str, str], str] = {
    ("draft", "candidate"): "promote_candidate",
    ("candidate", "approved"): "approve",
    ("validated", "approved"): "approve",
    ("approved", "active"): "activate",
    ("active", "deprecated"): "deprecate",
    ("approved", "deprecated"): "deprecate",
    ("active", "rolled_back"): "rollback",
}


@dataclass(frozen=True)
class LifecycleResult:
    version_id: str
    skill_id: str
    from_status: str
    to_status: str
    event_type: str
    actor: str
    reason: str


class UISkillLifecycleService:
    def transition(
        self,
        version_id: str,
        target_status: str,
        actor: str = "system",
        reason: str = "",
    ) -> LifecycleResult:
        init_db()
        db = SessionLocal()
        try:
            version = get_ui_skill_version_record(db, version_id)
            if version is None:
                raise ValueError(f"Skill version '{version_id}' not found.")

            from_status = version.status
            allowed = _VALID_TRANSITIONS.get(from_status, set())
            if target_status not in allowed:
                raise ValueError(
                    f"Cannot transition version '{version_id}' from '{from_status}' to '{target_status}'. "
                    f"Allowed targets: {sorted(allowed) or 'none'}."
                )

            is_active = target_status == "active"
            if is_active:
                current_active = get_active_ui_skill_version(db, version.skill_id)
                if current_active and current_active.id != version_id:
                    raise ValueError(
                        f"Skill '{version.skill_id}' already has an active version '{current_active.id}'. "
                        "Deprecate or roll back the current active version first."
                    )

            deactivate = target_status in ("deprecated", "rolled_back") and version.is_active
            new_is_active = False if deactivate else is_active
            update_ui_skill_version_status(db, version_id, status=target_status, is_active=new_is_active)

            event_type = _EVENT_NAMES.get((from_status, target_status), f"{from_status}_to_{target_status}")
            create_ui_skill_version_lifecycle_event(
                db,
                version_id=version_id,
                skill_id=version.skill_id,
                event_type=event_type,
                from_status=from_status,
                to_status=target_status,
                actor=actor,
                reason=reason,
            )

            return LifecycleResult(
                version_id=version_id,
                skill_id=version.skill_id,
                from_status=from_status,
                to_status=target_status,
                event_type=event_type,
                actor=actor,
                reason=reason,
            )
        finally:
            db.close()

    def promote_to_candidate(self, version_id: str, actor: str = "system", reason: str = "") -> LifecycleResult:
        return self.transition(version_id, "candidate", actor=actor, reason=reason)

    def approve(self, version_id: str, actor: str = "system", reason: str = "") -> LifecycleResult:
        return self.transition(version_id, "approved", actor=actor, reason=reason)

    def activate(self, version_id: str, actor: str = "system", reason: str = "") -> LifecycleResult:
        return self.transition(version_id, "active", actor=actor, reason=reason)

    def deprecate(self, version_id: str, actor: str = "system", reason: str = "") -> LifecycleResult:
        return self.transition(version_id, "deprecated", actor=actor, reason=reason)
