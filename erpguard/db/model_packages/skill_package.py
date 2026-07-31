"""Compiled skill package persistence (master spec section 18, Phase 19 19.4).

Content (`package_json`/`validation_result_json`/`package_hash`/
`candidate_id`/`proof_id`) is set once at compile time and never changes --
enforced below regardless of `status`. `status` walks a directed lifecycle
`compiled -> approved -> canary -> active -> rolled_back`, with `deprecated`
reachable from `active` (superseded by a promotion, not rolled back -- that
word is reserved for an active package pulled due to a real problem) and
re-promotable `deprecated -> active` (rollback restoring a prior version).
Only `rolled_back` is terminal. The listener below is the last-resort guard;
`erpguard.domain.deployment.service.SkillDeploymentService` is what actually
walks the state machine and writes the paired `SkillDeploymentEvent`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class SkillPackage(Base):
    __tablename__ = "skill_packages"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    proof_id: Mapped[str] = mapped_column(String(128), nullable=False)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    candidate_version: Mapped[str] = mapped_column(String(64), nullable=False)
    connector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="compiled")
    package_json: Mapped[str] = mapped_column(Text, nullable=False)
    validation_result_json: Mapped[str] = mapped_column(Text, nullable=False)
    package_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_TERMINAL_STATUSES = {"rolled_back"}
_IMMUTABLE_CONTENT_ATTRS = (
    "package_json",
    "validation_result_json",
    "package_hash",
    "candidate_id",
    "proof_id",
    "process_key",
    "candidate_version",
    "connector_id",
)


@event.listens_for(SkillPackage, "before_update")
def reject_invalid_skill_package_update(mapper, connection, target) -> None:
    state = inspect(target)
    for attr in _IMMUTABLE_CONTENT_ATTRS:
        history = state.attrs[attr].history
        if history.deleted:
            raise ValueError(f"skill_package_{attr}_immutable")

    status_history = state.attrs.status.history
    previous_status = status_history.deleted[0] if status_history.deleted else target.status
    if previous_status in _TERMINAL_STATUSES and status_history.deleted:
        raise ValueError("terminal_skill_package_status_immutable")
