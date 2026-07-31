"""Add immutable analytical snapshots, quality reports and margin analyses."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0019_decision_intelligence"
down_revision = "0018_operational_shadow_feed"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "analytical_snapshots" not in existing:
        op.create_table(
            "analytical_snapshots",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("connection_id", sa.String(128), nullable=False, index=True),
            sa.Column("company_ids_json", sa.Text(), nullable=False),
            sa.Column("period_start", sa.String(10), nullable=False),
            sa.Column("period_end", sa.String(10), nullable=False),
            sa.Column("comparison_period_start", sa.String(10), nullable=False),
            sa.Column("comparison_period_end", sa.String(10), nullable=False),
            sa.Column("source_models_json", sa.Text(), nullable=False),
            sa.Column("extraction_manifest_json", sa.Text(), nullable=False),
            sa.Column("row_counts_json", sa.Text(), nullable=False),
            sa.Column("currency", sa.String(16), nullable=True),
            sa.Column("source_hash", sa.String(128), nullable=False, index=True),
            sa.Column("metric_definition_version", sa.String(64), nullable=False),
            sa.Column("extraction_payload_json", sa.Text(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "analytical_data_quality_reports" not in existing:
        op.create_table(
            "analytical_data_quality_reports",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("snapshot_id", sa.String(128), nullable=False, index=True),
            sa.Column("checks_json", sa.Text(), nullable=False),
            sa.Column("errors_json", sa.Text(), nullable=False),
            sa.Column("warnings_json", sa.Text(), nullable=False),
            sa.Column("cost_coverage_rate", sa.Float(), nullable=False),
            sa.Column("revenue_coverage_rate", sa.Float(), nullable=False),
            sa.Column("duplicate_rate", sa.Float(), nullable=False),
            sa.Column("refund_reconciliation_rate", sa.Float(), nullable=False),
            sa.Column("confidence_grade", sa.String(8), nullable=False),
            sa.Column("blocking_issues_json", sa.Text(), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "margin_analyses" not in existing:
        op.create_table(
            "margin_analyses",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("snapshot_id", sa.String(128), nullable=False, index=True),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("metric_definition_version", sa.String(64), nullable=False),
            sa.Column("current_metrics_json", sa.Text(), nullable=False),
            sa.Column("comparison_metrics_json", sa.Text(), nullable=False),
            sa.Column("margin_bridge_json", sa.Text(), nullable=False),
            sa.Column("product_drivers_json", sa.Text(), nullable=False),
            sa.Column("customer_drivers_json", sa.Text(), nullable=False),
            sa.Column("warnings_json", sa.Text(), nullable=False),
            sa.Column("tolerance", sa.Float(), nullable=False),
            sa.Column("repeat_number", sa.Integer(), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    for table in (
        "margin_analyses",
        "analytical_data_quality_reports",
        "analytical_snapshots",
    ):
        if table in existing:
            op.drop_table(table)
