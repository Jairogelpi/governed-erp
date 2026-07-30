"""Phase 18 append-only shadow deployment persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ShadowDeployment(Base):
    __tablename__ = "shadow_deployments"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    candidate_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    proof_id: Mapped[str] = mapped_column(String(128), nullable=False)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    active_version: Mapped[str] = mapped_column(String(64), nullable=False)
    candidate_version: Mapped[str] = mapped_column(String(64), nullable=False)
    object_type: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="shadow")
    agreement_threshold: Mapped[float] = mapped_column(Float, nullable=False)
    minimum_case_count: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    minimum_decision_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)
    minimum_review_coverage: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    minimum_outcome_reconciliation: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    observation_window_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=168)
    no_effects: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ShadowCaseResult(Base):
    __tablename__ = "shadow_case_results"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "deployment_id",
            "idempotency_key",
            name="uq_shadow_case_tenant_deployment_idempotency",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    case_id: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    input_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    active_decision_json: Mapped[str] = mapped_column(Text, nullable=False)
    candidate_decision_json: Mapped[str] = mapped_column(Text, nullable=False)
    agreement: Mapped[bool] = mapped_column(Boolean, nullable=False)
    difference_categories_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    actual_outcome_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    evaluation_mode: Mapped[str] = mapped_column(String(32), nullable=False, default="manual_api")
    canonical_trace_hash: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    trace_provenance_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    variant_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    first_event_at: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_event_at: Mapped[str | None] = mapped_column(String(100), nullable=True)
    deterministic_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    evaluated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ShadowCaseReview(Base):
    __tablename__ = "shadow_case_reviews"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    shadow_case_result_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    reviewer_id: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str] = mapped_column(Text, nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ShadowOutcomeObservation(Base):
    __tablename__ = "shadow_outcome_observations"
    __table_args__ = (
        UniqueConstraint(
            "tenant_id",
            "shadow_case_result_id",
            "idempotency_key",
            name="uq_shadow_outcome_case_idempotency",
        ),
    )

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    shadow_case_result_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    idempotency_key: Mapped[str] = mapped_column(String(256), nullable=False)
    outcome_json: Mapped[str] = mapped_column(Text, nullable=False)
    observed_decision_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    provenance: Mapped[str] = mapped_column(String(32), nullable=False)
    source_event_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    recorded_by: Mapped[str] = mapped_column(String(128), nullable=False)
    deterministic_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


class ShadowFeedRun(Base):
    __tablename__ = "shadow_feed_runs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    deployment_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    trigger: Mapped[str] = mapped_column(String(32), nullable=False)
    requested_case_ids_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    scanned_case_count: Mapped[int] = mapped_column(Integer, nullable=False)
    evaluated_case_count: Mapped[int] = mapped_column(Integer, nullable=False)
    deduplicated_case_count: Mapped[int] = mapped_column(Integer, nullable=False)
    failed_case_count: Mapped[int] = mapped_column(Integer, nullable=False)
    failure_codes_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    no_effects: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


@event.listens_for(ShadowDeployment, "before_update")
@event.listens_for(ShadowDeployment, "before_delete")
@event.listens_for(ShadowCaseResult, "before_update")
@event.listens_for(ShadowCaseResult, "before_delete")
@event.listens_for(ShadowCaseReview, "before_update")
@event.listens_for(ShadowCaseReview, "before_delete")
@event.listens_for(ShadowOutcomeObservation, "before_update")
@event.listens_for(ShadowOutcomeObservation, "before_delete")
@event.listens_for(ShadowFeedRun, "before_update")
@event.listens_for(ShadowFeedRun, "before_delete")
def reject_shadow_mutation(mapper, connection, target) -> None:
    raise ValueError("shadow_evidence_immutable")
