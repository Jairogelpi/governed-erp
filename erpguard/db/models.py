from datetime import datetime, timezone

from sqlalchemy import DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    erp_type: Mapped[str] = mapped_column(Text, nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    config_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )


class PreflightCase(Base):
    __tablename__ = "preflight_cases"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    connection_id: Mapped[str] = mapped_column(Text, nullable=False)
    actor_json: Mapped[str] = mapped_column(Text, nullable=False)
    action_json: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_action: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_object: Mapped[str] = mapped_column(Text, nullable=False)
    state_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False)
    simulation_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    decision: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[str] = mapped_column(Text, nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class InvariantResult(Base):
    __tablename__ = "invariant_results"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    preflight_case_id: Mapped[str] = mapped_column(Text, nullable=False)
    invariant_id: Mapped[str] = mapped_column(Text, nullable=False)
    invariant_type: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(Text, nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    case_id: Mapped[str] = mapped_column(Text, nullable=False)
    event_type: Mapped[str] = mapped_column(Text, nullable=False)
    event_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class Policy(Base):
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    version: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_action: Mapped[str] = mapped_column(Text, nullable=False)
    canonical_object: Mapped[str] = mapped_column(Text, nullable=False)
    erp_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    industry_scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    policy_yaml: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )
