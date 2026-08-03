"""User-declared write capabilities.

A declared capability names one bounded write shape on Odoo -- update
one field on up to `max_records_per_run` existing records
(`operation="update_field"`), create one record with a fixed, declared
field set (`operation="create_record"`), or archive records by setting
`active=False` (`operation="archive_record"`, always reversible: the
same declaration re-run with `value=True`, or a second `update_field`
capability, restores it -- there is deliberately no real `unlink` path
anywhere in this codebase). It is never a generic write. Same
content-freeze/terminal-status idiom as `SkillPackage`: content locks
once `approved_at is not None`, only `rejected`/`deprecated` are
terminal (an `active` capability can be `deprecate`d but never revived,
matching real capability retirement -- unlike `SkillPackage`'s
`deprecated -> active` restore path, there's no "rollback" concept here
since nothing supersedes a declared capability, it's just turned off).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DeclaredWriteCapability(Base):
    __tablename__ = "declared_write_capabilities"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    operation: Mapped[str] = mapped_column(String(32), nullable=False, default="update_field")
    target_model: Mapped[str] = mapped_column(String(128), nullable=False)
    target_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    field_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    minimum_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    maximum_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    allowed_values_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    required_fields_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    idempotency_field: Mapped[str | None] = mapped_column(String(128), nullable=True)
    max_records_per_run: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_TERMINAL_STATUSES = {"rejected", "deprecated"}
_IMMUTABLE_CONTENT_ATTRS = (
    "operation",
    "target_model",
    "target_field",
    "field_type",
    "minimum_value",
    "maximum_value",
    "allowed_values_json",
    "required_fields_json",
    "idempotency_field",
    "max_records_per_run",
    "content_hash",
)


@event.listens_for(DeclaredWriteCapability, "before_update")
def reject_invalid_declared_capability_update(mapper, connection, target) -> None:
    state = inspect(target)
    approved_history = state.attrs.approved_at.history
    was_approved = (approved_history.deleted[0] if approved_history.deleted else target.approved_at) is not None
    if was_approved:
        for attr in _IMMUTABLE_CONTENT_ATTRS:
            if state.attrs[attr].history.deleted:
                raise ValueError(f"declared_write_capability_{attr}_immutable")

    status_history = state.attrs.status.history
    previous_status = status_history.deleted[0] if status_history.deleted else target.status
    if previous_status in _TERMINAL_STATUSES and status_history.deleted:
        raise ValueError("terminal_declared_write_capability_status_immutable")
