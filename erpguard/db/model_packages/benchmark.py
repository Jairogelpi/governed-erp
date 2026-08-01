"""Spec 93 -- ERPRiskBench run/result persistence. `BenchmarkRun` tracks
one benchmark execution (a dataset version x set of configurations x
repeat count); `BenchmarkCaseResult` is the append-only per-case-per-
configuration-per-repeat raw result the report is generated from (Sec
28.4: "raw results retained", "report generated from data, not edited
manually")."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, Integer, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BenchmarkRun(Base):
    __tablename__ = "benchmark_runs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(128), nullable=False)
    dataset_manifest_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    configurations_json: Mapped[str] = mapped_column(Text, nullable=False)
    repeats: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class BenchmarkCaseResult(Base):
    __tablename__ = "benchmark_case_results"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    benchmark_run_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    configuration: Mapped[str] = mapped_column(String(32), nullable=False)
    case_id: Mapped[str] = mapped_column(String(128), nullable=False)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    repeat_index: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    outcome_json: Mapped[str] = mapped_column(Text, nullable=False)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    token_cost: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


@event.listens_for(BenchmarkCaseResult, "before_update")
@event.listens_for(BenchmarkCaseResult, "before_delete")
def reject_benchmark_case_result_mutation(mapper, connection, target) -> None:
    raise ValueError("benchmark_case_result_immutable")
