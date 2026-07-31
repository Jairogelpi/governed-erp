"""Phase 19 append-only skill deployment lifecycle events.

The "active version pointer" is derived, not stored: the active
`SkillPackage` for a `(tenant_id, process_key)` is whichever package
currently has `status == "active"` (enforced to be at most one by
`SkillDeploymentService`), and the history of how it got there lives here,
append-only, same idiom as `ShadowDeployment`'s evidence tables
(`erpguard/db/model_packages/shadow.py`).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SkillDeploymentEvent(Base):
    __tablename__ = "skill_deployment_events"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    skill_package_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)
    from_status: Mapped[str] = mapped_column(String(32), nullable=False)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    shadow_deployment_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reason: Mapped[str] = mapped_column(Text, nullable=False, default="")
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


@event.listens_for(SkillDeploymentEvent, "before_update")
@event.listens_for(SkillDeploymentEvent, "before_delete")
def reject_skill_deployment_event_mutation(mapper, connection, target) -> None:
    raise ValueError("skill_deployment_event_immutable")
