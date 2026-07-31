"""Add Spec 92 Workstream C outcome measurement."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0024_outcome_measurement"
down_revision = "0023_operational_canary_router"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "outcome_measurement_plans" not in existing:
        op.create_table(
            "outcome_measurement_plans",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("recommendation_id", sa.String(128), nullable=False, index=True),
            sa.Column("margin_opportunity_id", sa.String(128), nullable=False),
            sa.Column("baseline_snapshot_id", sa.String(128), nullable=False),
            sa.Column("baseline_analysis_id", sa.String(128), nullable=False),
            sa.Column("action_draft_id", sa.String(128), nullable=False),
            sa.Column("execution_run_ids_json", sa.Text(), nullable=False),
            sa.Column("metric_definition_version", sa.String(64), nullable=False),
            sa.Column("target_metrics_json", sa.Text(), nullable=False),
            sa.Column("population_scope_json", sa.Text(), nullable=False),
            sa.Column("comparison_method", sa.String(32), nullable=False),
            sa.Column("observation_start", sa.String(10), nullable=False),
            sa.Column("observation_end", sa.String(10), nullable=False),
            sa.Column("minimum_data_coverage", sa.Float(), nullable=False),
            sa.Column("assumptions_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "outcome_observations" not in existing:
        op.create_table(
            "outcome_observations",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("measurement_plan_id", sa.String(128), nullable=False, index=True),
            sa.Column("followup_snapshot_id", sa.String(128), nullable=True),
            sa.Column("followup_analysis_id", sa.String(128), nullable=True),
            sa.Column("source", sa.String(32), nullable=False),
            sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("metrics_json", sa.Text(), nullable=False),
            sa.Column("quality_json", sa.Text(), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "realized_outcome_reports" not in existing:
        op.create_table(
            "realized_outcome_reports",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("measurement_plan_id", sa.String(128), nullable=False, index=True),
            sa.Column("recommendation_id", sa.String(128), nullable=False),
            sa.Column("opportunity_id", sa.String(128), nullable=False),
            sa.Column("estimated_conservative", sa.String(64), nullable=False),
            sa.Column("estimated_base", sa.String(64), nullable=False),
            sa.Column("estimated_optimistic", sa.String(64), nullable=False),
            sa.Column("observed_revenue_change", sa.String(64), nullable=True),
            sa.Column("observed_margin_change", sa.String(64), nullable=True),
            sa.Column("observed_margin_percent_change", sa.String(64), nullable=True),
            sa.Column("observed_refund_change", sa.String(64), nullable=True),
            sa.Column("realized_value", sa.String(64), nullable=True),
            sa.Column("variance_from_base_estimate", sa.String(64), nullable=True),
            sa.Column("result_classification", sa.String(32), nullable=False),
            sa.Column("confidence_band", sa.String(16), nullable=False),
            sa.Column("limitations_json", sa.Text(), nullable=False),
            sa.Column("assumptions_json", sa.Text(), nullable=False),
            sa.Column("metric_definition_version", sa.String(64), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    for table in ("realized_outcome_reports", "outcome_observations", "outcome_measurement_plans"):
        if table in existing:
            op.drop_table(table)
