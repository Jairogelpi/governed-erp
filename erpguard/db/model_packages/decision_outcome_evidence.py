"""Spec 92 Workstream D: `DecisionOutcomeEvidenceBundle` -- the single
sealed record that reconstructs data -> diagnosis -> recommendation ->
execution -> observed result (Sec 11).

Lifecycle: `building -> complete -> sealed` or `building -> incomplete`
(rebuilding a `building`/`incomplete` bundle is allowed and idempotent --
`DecisionOutcomeEvidenceService.build` re-runs it as new evidence appears
in the lifecycle it references). Once `sealed`, the row is fully immutable,
same idiom as `RealizedOutcomeReport`.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class DecisionOutcomeEvidenceBundle(Base):
    __tablename__ = "decision_outcome_evidence_bundles"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    measurement_plan_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="building")
    manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    missing_resources_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    chain_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    sealed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sealed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)


@event.listens_for(DecisionOutcomeEvidenceBundle, "before_update")
def reject_sealed_bundle_update(mapper, connection, target) -> None:
    state = inspect(target)
    status_history = state.attrs.status.history
    previous_status = status_history.deleted[0] if status_history.deleted else target.status
    if previous_status == "sealed":
        raise ValueError("decision_outcome_evidence_bundle_sealed_immutable")


@event.listens_for(DecisionOutcomeEvidenceBundle, "before_delete")
def reject_bundle_delete(mapper, connection, target) -> None:
    raise ValueError("decision_outcome_evidence_bundle_immutable")
