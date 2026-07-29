"""Immutable Proof of Improvement persistence (master spec section 17)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, event
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ProcessProof(Base):
    __tablename__ = "process_proofs"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    baseline_replay_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    candidate_replay_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    dataset_version: Mapped[str] = mapped_column(String(128), nullable=False)
    benchmark_version: Mapped[str] = mapped_column(String(128), nullable=False)
    metric_comparisons_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    regressions_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    safety_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    reproducibility_summary_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    evidence_refs_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    recommendation_basis_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    limitations_json: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)


@event.listens_for(ProcessProof, "before_update")
def reject_proof_update(mapper, connection, target) -> None:
    """Proofs are immutable from creation (spec 17.4) -- new data creates a
    new proof, an existing one is never edited."""

    raise ValueError("proof_of_improvement_immutable")
