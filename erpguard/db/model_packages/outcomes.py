"""Spec 92 Workstream C: measure the observed business result after an
approved, executed `GovernedRecommendation`, without claiming causality.

Same content-freeze/terminal-status idiom as every other Workstream
A/B model (`skill_package.py`'s pattern). `OutcomeObservation` is
append-only evidence, same idiom as `ShadowDeployment`'s children.
`RealizedOutcomeReport` is fully immutable, same idiom as `MarginOpportunity`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OutcomeMeasurementPlan(Base):
    __tablename__ = "outcome_measurement_plans"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    margin_opportunity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    baseline_snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    baseline_analysis_id: Mapped[str] = mapped_column(String(128), nullable=False)
    action_draft_id: Mapped[str] = mapped_column(String(128), nullable=False)
    execution_run_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    metric_definition_version: Mapped[str] = mapped_column(String(64), nullable=False)
    target_metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    population_scope_json: Mapped[str] = mapped_column(Text, nullable=False)
    comparison_method: Mapped[str] = mapped_column(String(32), nullable=False)
    observation_start: Mapped[str] = mapped_column(String(10), nullable=False)
    observation_end: Mapped[str] = mapped_column(String(10), nullable=False)
    minimum_data_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.8)
    assumptions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class OutcomeObservation(Base):
    __tablename__ = "outcome_observations"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    measurement_plan_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    followup_snapshot_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    followup_analysis_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    quality_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class RealizedOutcomeReport(Base):
    __tablename__ = "realized_outcome_reports"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    measurement_plan_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(128), nullable=False)
    opportunity_id: Mapped[str] = mapped_column(String(128), nullable=False)
    estimated_conservative: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_base: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_optimistic: Mapped[str] = mapped_column(String(64), nullable=False)
    observed_revenue_change: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_margin_change: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_margin_percent_change: Mapped[str | None] = mapped_column(String(64), nullable=True)
    observed_refund_change: Mapped[str | None] = mapped_column(String(64), nullable=True)
    realized_value: Mapped[str | None] = mapped_column(String(64), nullable=True)
    variance_from_base_estimate: Mapped[str | None] = mapped_column(String(64), nullable=True)
    result_classification: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(16), nullable=False)
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    assumptions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    metric_definition_version: Mapped[str] = mapped_column(String(64), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


_PLAN_IMMUTABLE_ATTRS = (
    "recommendation_id",
    "margin_opportunity_id",
    "baseline_snapshot_id",
    "baseline_analysis_id",
    "action_draft_id",
    "execution_run_ids_json",
    "metric_definition_version",
    "target_metrics_json",
    "population_scope_json",
    "comparison_method",
    "observation_start",
    "observation_end",
    "minimum_data_coverage",
    "content_hash",
)
_PLAN_TERMINAL_STATUSES = {"evaluated", "blocked", "inconclusive"}


@event.listens_for(OutcomeMeasurementPlan, "before_update")
def reject_invalid_measurement_plan_update(mapper, connection, target) -> None:
    state = inspect(target)
    started_history = state.attrs.started_at.history
    was_started = (started_history.deleted[0] if started_history.deleted else target.started_at) is not None
    if was_started:
        for attr in _PLAN_IMMUTABLE_ATTRS:
            if state.attrs[attr].history.deleted:
                raise ValueError(f"outcome_measurement_plan_{attr}_immutable")

    status_history = state.attrs.status.history
    previous_status = status_history.deleted[0] if status_history.deleted else target.status
    if previous_status in _PLAN_TERMINAL_STATUSES and status_history.deleted:
        raise ValueError("terminal_outcome_measurement_plan_status_immutable")


@event.listens_for(OutcomeObservation, "before_update")
@event.listens_for(OutcomeObservation, "before_delete")
def reject_outcome_observation_mutation(mapper, connection, target) -> None:
    raise ValueError("outcome_observation_immutable")


@event.listens_for(RealizedOutcomeReport, "before_update")
@event.listens_for(RealizedOutcomeReport, "before_delete")
def reject_realized_outcome_report_mutation(mapper, connection, target) -> None:
    raise ValueError("realized_outcome_report_immutable")
