"""Immutable Phase 16.5 analytical truth-layer persistence."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class AnalyticalSnapshot(Base):
    __tablename__ = "analytical_snapshots"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    connection_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    company_ids_json: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[str] = mapped_column(String(10), nullable=False)
    period_end: Mapped[str] = mapped_column(String(10), nullable=False)
    comparison_period_start: Mapped[str] = mapped_column(String(10), nullable=False)
    comparison_period_end: Mapped[str] = mapped_column(String(10), nullable=False)
    source_models_json: Mapped[str] = mapped_column(Text, nullable=False)
    extraction_manifest_json: Mapped[str] = mapped_column(Text, nullable=False)
    row_counts_json: Mapped[str] = mapped_column(Text, nullable=False)
    currency: Mapped[str | None] = mapped_column(String(16), nullable=True)
    source_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    metric_definition_version: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class DataQualityReport(Base):
    __tablename__ = "analytical_data_quality_reports"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    checks_json: Mapped[str] = mapped_column(Text, nullable=False)
    errors_json: Mapped[str] = mapped_column(Text, nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False)
    cost_coverage_rate: Mapped[float] = mapped_column(Float, nullable=False)
    revenue_coverage_rate: Mapped[float] = mapped_column(Float, nullable=False)
    duplicate_rate: Mapped[float] = mapped_column(Float, nullable=False)
    refund_reconciliation_rate: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_grade: Mapped[str] = mapped_column(String(8), nullable=False)
    blocking_issues_json: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


class MarginAnalysis(Base):
    __tablename__ = "margin_analyses"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_definition_version: Mapped[str] = mapped_column(String(64), nullable=False)
    current_metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    comparison_metrics_json: Mapped[str] = mapped_column(Text, nullable=False)
    margin_bridge_json: Mapped[str] = mapped_column(Text, nullable=False)
    product_drivers_json: Mapped[str] = mapped_column(Text, nullable=False)
    customer_drivers_json: Mapped[str] = mapped_column(Text, nullable=False)
    warnings_json: Mapped[str] = mapped_column(Text, nullable=False)
    tolerance: Mapped[float] = mapped_column(Float, nullable=False)
    repeat_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=utc_now,
        nullable=False,
    )


@event.listens_for(AnalyticalSnapshot, "before_update")
@event.listens_for(AnalyticalSnapshot, "before_delete")
@event.listens_for(DataQualityReport, "before_update")
@event.listens_for(DataQualityReport, "before_delete")
@event.listens_for(MarginAnalysis, "before_update")
@event.listens_for(MarginAnalysis, "before_delete")
def reject_analytical_mutation(mapper, connection, target) -> None:
    raise ValueError("analytical_evidence_immutable")
