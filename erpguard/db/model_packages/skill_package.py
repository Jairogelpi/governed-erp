"""Compiled skill package persistence (master spec section 18).

Content (`package_json`/`validation_result_json`/`package_hash`) is set once
at compile time and never changes. `status` transitions `compiled ->
approved` exactly once (mirrors `ProcessReplay`'s conditional freeze
listener, not `ProcessProof`'s unconditional-reject one -- a skill package
has one real state transition, a proof has none). No child rows exist (the
whole package is one JSON blob per row), so the header+child two-listener
pattern Phase 13.1 introduced for `ProcessReplayCase` isn't needed here.
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


@event.listens_for(SkillPackage, "before_update")
def reject_approved_skill_package_update(mapper, connection, target) -> None:
    history = inspect(target).attrs.status.history
    previous_status = history.deleted[0] if history.deleted else target.status
    if previous_status == "approved":
        raise ValueError("approved_skill_package_immutable")
