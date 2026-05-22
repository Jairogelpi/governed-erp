from __future__ import annotations

from dataclasses import dataclass, field

from erpguard.db.repositories import (
    get_ui_skill_version_record,
    list_ui_skill_version_lifecycle_events,
)
from erpguard.db.session import SessionLocal, init_db


@dataclass(frozen=True)
class LifecycleEventEntry:
    event_id: str
    version_id: str
    skill_id: str
    event_type: str
    from_status: str
    to_status: str
    actor: str
    reason: str
    created_at: str


@dataclass(frozen=True)
class LifecycleAuditResult:
    version_id: str
    skill_id: str
    current_status: str
    version_number: int
    events: list[LifecycleEventEntry] = field(default_factory=list)


class UISkillLifecycleAuditService:
    def get_events(self, version_id: str) -> LifecycleAuditResult | None:
        init_db()
        db = SessionLocal()
        try:
            version = get_ui_skill_version_record(db, version_id)
            if version is None:
                return None
            rows = list_ui_skill_version_lifecycle_events(db, version_id)
            return LifecycleAuditResult(
                version_id=version_id,
                skill_id=version.skill_id,
                current_status=version.status,
                version_number=version.version_number,
                events=[
                    LifecycleEventEntry(
                        event_id=r.id,
                        version_id=r.version_id,
                        skill_id=r.skill_id,
                        event_type=r.event_type,
                        from_status=r.from_status,
                        to_status=r.to_status,
                        actor=r.actor,
                        reason=r.reason,
                        created_at=r.created_at.isoformat(),
                    )
                    for r in rows
                ],
            )
        finally:
            db.close()
