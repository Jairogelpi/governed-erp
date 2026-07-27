"""Persistence boundary for future versioned process definitions.

This model is intentionally storage-only in Phase 2. It has no API, repository,
activation or execution behavior until a later approved phase.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProcessDefinition(Base):
    """Immutable-storage-ready process definition envelope."""

    __tablename__ = "process_definitions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    definition_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)

