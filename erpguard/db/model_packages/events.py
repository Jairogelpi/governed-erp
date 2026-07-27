"""Tenant-scoped canonical event, object and ingestion cursor models."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CanonicalObject(Base):
    __tablename__ = "canonical_objects"
    __table_args__ = (
        UniqueConstraint("tenant_id", "object_key", name="uq_canonical_object_identity"),
    )

    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    object_type: Mapped[str] = mapped_column(String(128), nullable=False)
    object_key: Mapped[str] = mapped_column(String(200), nullable=False)
    attributes_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


class CanonicalEvent(Base):
    __tablename__ = "canonical_events"
    __table_args__ = (UniqueConstraint("tenant_id", "event_key", name="uq_canonical_event_tenant_key"),)

    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    event_key: Mapped[str] = mapped_column(String(200), nullable=False)
    event_type: Mapped[str] = mapped_column(String(200), nullable=False)
    event_timestamp: Mapped[str] = mapped_column(String(100), nullable=False)
    source: Mapped[str] = mapped_column(String(200), nullable=False)
    object_keys_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    attributes_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class IngestionCursor(Base):
    __tablename__ = "ingestion_cursors"
    __table_args__ = (
        UniqueConstraint("tenant_id", "connector_id", "stream_key", name="uq_ingestion_cursor_scope"),
    )

    id: Mapped[str] = mapped_column(String(200), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    connector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    stream_key: Mapped[str] = mapped_column(String(200), nullable=False)
    cursor_value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)
