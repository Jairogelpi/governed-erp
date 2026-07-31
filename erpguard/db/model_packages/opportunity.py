"""Immutable Phase 16.6 opportunity/ROI evidence, derived from a reliable MarginAnalysis."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class MarginOpportunity(Base):
    __tablename__ = "margin_opportunities"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    margin_analysis_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    cause: Mapped[str] = mapped_column(String(64), nullable=False)
    affected_population_json: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_json: Mapped[str] = mapped_column(Text, nullable=False)
    impact_conservative: Mapped[str] = mapped_column(String(64), nullable=False)
    impact_base: Mapped[str] = mapped_column(String(64), nullable=False)
    impact_optimistic: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    implementation_cost: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payback_period_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    proposed_action: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="proposed")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


@event.listens_for(MarginOpportunity, "before_update")
@event.listens_for(MarginOpportunity, "before_delete")
def reject_margin_opportunity_mutation(mapper, connection, target) -> None:
    raise ValueError("margin_opportunity_immutable")
