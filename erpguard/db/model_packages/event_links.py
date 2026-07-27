"""Relational event-to-object links for scalable case projection."""

from __future__ import annotations

from sqlalchemy import String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


class CanonicalEventObject(Base):
    __tablename__ = "canonical_event_objects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "event_id", "object_id", "qualifier", name="uq_event_object_link"),
    )

    id: Mapped[str] = mapped_column(String(220), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    object_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    qualifier: Mapped[str] = mapped_column(Text, nullable=False, default="")
