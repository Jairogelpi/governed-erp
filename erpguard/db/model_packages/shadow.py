"""Phase 18 append-only shadow deployment persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Float, String, Text, UniqueConstraint, event
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


@event.listens_for(ShadowDeployment, "before_update")
@event.listens_for(ShadowDeployment, "before_delete")
@event.listens_for(ShadowCaseResult, "before_update")
@event.listens_for(ShadowCaseResult, "before_delete")
@event.listens_for(ShadowCaseReview, "before_update")
@event.listens_for(ShadowCaseReview, "before_delete")
def reject_shadow_mutation(mapper, connection, target) -> None:
    raise ValueError("shadow_evidence_immutable")
