"""Spec 92 Workstream B: deterministic canary routing on top of Phase 19's
skill lifecycle (`compiled -> approved -> canary -> active -> rolled_back`).

`CanaryPolicy` freezes its content once approved, same idiom as
`SkillPackage`. `CanaryRoutingDecision` and `CanarySafetyIncident` are
append-only evidence, same idiom as `ShadowDeployment`'s child tables --
except `CanarySafetyIncident` allows exactly one follow-up mutation
(`resolved_at`/`resolved_by`/`resolution_notes`, once, while unresolved).
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class CanaryPolicy(Base):
    __tablename__ = "canary_policies"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    stable_skill_package_id: Mapped[str] = mapped_column(String(128), nullable=False)
    canary_skill_package_id: Mapped[str] = mapped_column(String(128), nullable=False)
    shadow_deployment_id: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    percentage_basis_points: Mapped[int] = mapped_column(Integer, nullable=False)
    maximum_cases: Mapped[int] = mapped_column(Integer, nullable=False)
    maximum_total_amount: Mapped[float] = mapped_column(Float, nullable=False)
    allowed_capabilities_json: Mapped[str] = mapped_column(Text, nullable=False)
    company_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    minimum_amount: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    maximum_amount: Mapped[float] = mapped_column(Float, nullable=False)
    object_types_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    start_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    safety_thresholds_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paused_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    aborted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CanaryRoutingDecision(Base):
    __tablename__ = "canary_routing_decisions"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    canary_policy_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    business_object_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    routing_context_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    bucket: Mapped[int | None] = mapped_column(Integer, nullable=True)
    selected_lane: Mapped[str] = mapped_column(String(16), nullable=False)
    stable_skill_package_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    canary_skill_package_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selected_skill_package_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    selection_reason: Mapped[str] = mapped_column(String(64), nullable=False)
    execution_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class CanarySafetyIncident(Base):
    __tablename__ = "canary_safety_incidents"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    canary_policy_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    routing_decision_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    execution_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    incident_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    details_json: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_pack_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    resolution_notes: Mapped[str] = mapped_column(Text, nullable=False, default="")


_POLICY_IMMUTABLE_ATTRS = (
    "process_key",
    "stable_skill_package_id",
    "canary_skill_package_id",
    "shadow_deployment_id",
    "percentage_basis_points",
    "maximum_cases",
    "maximum_total_amount",
    "allowed_capabilities_json",
    "company_ids_json",
    "minimum_amount",
    "maximum_amount",
    "object_types_json",
    "safety_thresholds_json",
    "content_hash",
)
_POLICY_TERMINAL_STATUSES = {"completed", "aborted"}


@event.listens_for(CanaryPolicy, "before_update")
def reject_invalid_canary_policy_update(mapper, connection, target) -> None:
    state = inspect(target)
    approved_history = state.attrs.approved_by.history
    was_approved = (approved_history.deleted[0] if approved_history.deleted else target.approved_by) is not None
    if was_approved:
        for attr in _POLICY_IMMUTABLE_ATTRS:
            if state.attrs[attr].history.deleted:
                raise ValueError(f"canary_policy_{attr}_immutable")

    status_history = state.attrs.status.history
    previous_status = status_history.deleted[0] if status_history.deleted else target.status
    if previous_status in _POLICY_TERMINAL_STATUSES and status_history.deleted:
        raise ValueError("terminal_canary_policy_status_immutable")


@event.listens_for(CanaryRoutingDecision, "before_update")
@event.listens_for(CanaryRoutingDecision, "before_delete")
def reject_canary_routing_decision_mutation(mapper, connection, target) -> None:
    raise ValueError("canary_routing_decision_immutable")


_INCIDENT_MUTABLE_ATTRS = {"resolved_at", "resolved_by", "resolution_notes"}


@event.listens_for(CanarySafetyIncident, "before_update")
def reject_invalid_incident_update(mapper, connection, target) -> None:
    state = inspect(target)
    for attr_name, attr_state in state.attrs.items():
        if attr_name in _INCIDENT_MUTABLE_ATTRS:
            continue
        if attr_state.history.deleted:
            raise ValueError(f"canary_safety_incident_{attr_name}_immutable")

    resolved_history = state.attrs.resolved_at.history
    previous_resolved_at = resolved_history.deleted[0] if resolved_history.deleted else target.resolved_at
    if previous_resolved_at is not None and resolved_history.deleted:
        raise ValueError("canary_safety_incident_already_resolved_immutable")


@event.listens_for(CanarySafetyIncident, "before_delete")
def reject_incident_delete(mapper, connection, target) -> None:
    raise ValueError("canary_safety_incident_immutable")
