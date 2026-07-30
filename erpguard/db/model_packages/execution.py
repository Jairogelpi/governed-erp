"""Execution Permit runtime persistence (master spec section 19 / Phase 15).

`ExecutionRun` carries a `Run`'s state machine: `planned -> approved ->
succeeded|blocked|failed|unknown`, or `revoked` before execution. Terminal
rows are immutable. The legacy `executed` value remains terminal for rows
created before Phase 17.

`Approval` is single-use: once bound to a run (`used_by_run_id` set) it is
immutable, enforced the same way.

`KillSwitch` is a simple per-tenant on/off flag, not a broader
circuit-breaker system -- see `erpguard/domain/execution/kill_switch_service.py`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ExecutionRun(Base):
    __tablename__ = "execution_runs_v2"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    connection_id: Mapped[str] = mapped_column(String(128), nullable=False)
    connector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_package_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    process_version_id: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_version_id: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(128), nullable=False)
    action_plan_json: Mapped[str] = mapped_column(Text, nullable=False)
    native_plan_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    state_snapshot_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    operation_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    native_plan_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    state_snapshot_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    capability_allowlist_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    approval_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    signature: Mapped[str] = mapped_column(String(256), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="planned")
    single_use: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    verification_result_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_pack_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    cleanup_plan_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    control_contract_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    control_contract_hash: Mapped[str] = mapped_column(String(128), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Approval(Base):
    __tablename__ = "execution_approvals"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    actor_id: Mapped[str] = mapped_column(String(128), nullable=False)
    scope: Mapped[str] = mapped_column(String(256), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    used_by_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)


class KillSwitch(Base):
    __tablename__ = "execution_kill_switches"

    tenant_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


_TERMINAL_RUN_STATUSES = {"executed", "succeeded", "blocked", "failed", "unknown", "revoked"}


@event.listens_for(ExecutionRun, "before_update")
def reject_terminal_run_update(mapper, connection, target) -> None:
    history = inspect(target).attrs.status.history
    previous_status = history.deleted[0] if history.deleted else target.status
    if previous_status in _TERMINAL_RUN_STATUSES:
        raise ValueError("execution_run_terminal_immutable")


@event.listens_for(Approval, "before_update")
def reject_used_approval_update(mapper, connection, target) -> None:
    history = inspect(target).attrs.used_at.history
    previous_used_at = history.deleted[0] if history.deleted else target.used_at
    if previous_used_at is not None:
        raise ValueError("approval_already_used_immutable")
