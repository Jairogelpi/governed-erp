"""Spec 92 Workstream A: MarginOpportunity -> GovernedRecommendation -> GovernedActionDraft.

Both tables freeze their content columns once the row leaves its earliest
mutable status (`draft`), same idiom as `SkillPackage`
(`erpguard/db/model_packages/skill_package.py`): named content attrs become
permanently immutable, and a terminal-status set blocks further transitions.
The allowed-transition graph itself is walked by
`erpguard.application.recommendations.service.RecommendationService`, not
enforced here -- this listener is the last-resort guard.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text, event, inspect
from sqlalchemy.orm import Mapped, mapped_column

from erpguard.db.base import Base


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class GovernedRecommendation(Base):
    __tablename__ = "governed_recommendations"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    margin_opportunity_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    margin_analysis_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    snapshot_id: Mapped[str] = mapped_column(String(128), nullable=False)
    recommendation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    business_rationale_json: Mapped[str] = mapped_column(Text, nullable=False)
    affected_population_json: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_impact_conservative: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_impact_base: Mapped[str] = mapped_column(String(64), nullable=False)
    estimated_impact_optimistic: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence_band: Mapped[str] = mapped_column(String(16), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    selected_action_template: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    source_content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GovernedActionDraft(Base):
    __tablename__ = "governed_action_drafts"

    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    recommendation_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    action_template: Mapped[str] = mapped_column(String(64), nullable=False)
    action_template_version: Mapped[str] = mapped_column(String(16), nullable=False)
    connector_id: Mapped[str] = mapped_column(String(128), nullable=False)
    process_key: Mapped[str] = mapped_column(String(128), nullable=False)
    capability: Mapped[str] = mapped_column(String(128), nullable=False)
    connection_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    constraints_json: Mapped[str] = mapped_column(Text, nullable=False)
    required_inputs_json: Mapped[str] = mapped_column(Text, nullable=False)
    preflight_spec_json: Mapped[str] = mapped_column(Text, nullable=False)
    postcondition_spec_json: Mapped[str] = mapped_column(Text, nullable=False)
    compensation_spec_json: Mapped[str] = mapped_column(Text, nullable=False)
    execution_classification: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="draft")
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    created_by: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    converted_run_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_RECOMMENDATION_IMMUTABLE_ATTRS = (
    "margin_opportunity_id",
    "margin_analysis_id",
    "snapshot_id",
    "recommendation_type",
    "title",
    "business_rationale_json",
    "affected_population_json",
    "estimated_impact_conservative",
    "estimated_impact_base",
    "estimated_impact_optimistic",
    "confidence_band",
    "risk_level",
    "selected_action_template",
    "source_content_hash",
    "content_hash",
)
_RECOMMENDATION_TERMINAL_STATUSES = {"rejected", "expired", "converted"}


@event.listens_for(GovernedRecommendation, "before_update")
def reject_invalid_recommendation_update(mapper, connection, target) -> None:
    state = inspect(target)
    submitted_history = state.attrs.submitted_at.history
    was_submitted = (
        submitted_history.deleted[0] if submitted_history.deleted else target.submitted_at
    ) is not None
    if was_submitted:
        for attr in _RECOMMENDATION_IMMUTABLE_ATTRS:
            if state.attrs[attr].history.deleted:
                raise ValueError(f"governed_recommendation_{attr}_immutable")

    status_history = state.attrs.status.history
    previous_status = status_history.deleted[0] if status_history.deleted else target.status
    if previous_status in _RECOMMENDATION_TERMINAL_STATUSES and status_history.deleted:
        raise ValueError("terminal_governed_recommendation_status_immutable")


_ACTION_DRAFT_IMMUTABLE_ATTRS = (
    "recommendation_id",
    "action_template",
    "action_template_version",
    "connector_id",
    "process_key",
    "capability",
    "arguments_json",
    "constraints_json",
    "execution_classification",
    "content_hash",
)
_ACTION_DRAFT_TERMINAL_STATUSES = {"invalidated", "converted"}


@event.listens_for(GovernedActionDraft, "before_update")
def reject_invalid_action_draft_update(mapper, connection, target) -> None:
    state = inspect(target)
    validated_history = state.attrs.validated_at.history
    was_validated = (
        validated_history.deleted[0] if validated_history.deleted else target.validated_at
    ) is not None
    if was_validated:
        for attr in _ACTION_DRAFT_IMMUTABLE_ATTRS:
            if state.attrs[attr].history.deleted:
                raise ValueError(f"governed_action_draft_{attr}_immutable")

    status_history = state.attrs.status.history
    previous_status = status_history.deleted[0] if status_history.deleted else target.status
    if previous_status in _ACTION_DRAFT_TERMINAL_STATUSES and status_history.deleted:
        raise ValueError("terminal_governed_action_draft_status_immutable")
