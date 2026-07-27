"""Immutable-after-submission process candidate persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, UniqueConstraint, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProcessCandidate(Base):
    __tablename__ = "process_candidates"
    __table_args__ = (
        UniqueConstraint("process_key", "candidate_version", name="uq_process_candidate_version"),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    base_version: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_version: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    changes_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


@event.listens_for(ProcessCandidate, "before_update")
def reject_submitted_candidate_update(mapper, connection, target) -> None:
    history = inspect(target).attrs.status.history
    previous_status = history.deleted[0] if history.deleted else target.status
    if previous_status == "submitted":
        raise ValueError("submitted_candidate_immutable")
