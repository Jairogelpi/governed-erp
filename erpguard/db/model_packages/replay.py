"""Immutable-after-freeze historical replay persistence (master spec section 15)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProcessReplay(Base):
    __tablename__ = "process_replays"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="running")
    policy_version: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    connector_simulator_version: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    frozen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ProcessReplayCase(Base):
    __tablename__ = "process_replay_cases"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    replay_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    decision_trace_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    predicted_effects_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    safety_violations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    regressions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    deterministic_trace_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    declared_decision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evaluated_decision_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unsupported_decisions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    decision_coverage_rate: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


def _reject_if_frozen(mapper, connection, target) -> None:
    history = inspect(target).attrs.status.history
    previous_status = history.deleted[0] if history.deleted else target.status
    if previous_status == "frozen":
        raise ValueError("frozen_replay_immutable")


@event.listens_for(ProcessReplay, "before_update")
def reject_frozen_replay_update(mapper, connection, target) -> None:
    _reject_if_frozen(mapper, connection, target)


def _parent_replay_is_frozen(connection, tenant_id: str, replay_id: str) -> bool:
    row = connection.execute(
        ProcessReplay.__table__.select()
        .with_only_columns(ProcessReplay.__table__.c.status)
        .where(
            ProcessReplay.__table__.c.id == replay_id,
            ProcessReplay.__table__.c.tenant_id == tenant_id,
        )
    ).first()
    return row is not None and row[0] == "frozen"


@event.listens_for(ProcessReplayCase, "before_update")
def reject_case_update_when_replay_frozen(mapper, connection, target) -> None:
    if _parent_replay_is_frozen(connection, target.tenant_id, target.replay_id):
        raise ValueError("frozen_replay_case_immutable")


@event.listens_for(ProcessReplayCase, "before_delete")
def reject_case_delete_when_replay_frozen(mapper, connection, target) -> None:
    if _parent_replay_is_frozen(connection, target.tenant_id, target.replay_id):
        raise ValueError("frozen_replay_case_immutable")
