"""Add Spec 92 Workstream A governed recommendations and action drafts."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0022_recommendation_action_drafts"
down_revision = "0021_margin_opportunities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "governed_recommendations" not in existing:
        op.create_table(
            "governed_recommendations",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("margin_opportunity_id", sa.String(128), nullable=False, index=True),
            sa.Column("margin_analysis_id", sa.String(128), nullable=False, index=True),
            sa.Column("snapshot_id", sa.String(128), nullable=False),
            sa.Column("recommendation_type", sa.String(32), nullable=False),
            sa.Column("title", sa.String(256), nullable=False),
            sa.Column("business_rationale_json", sa.Text(), nullable=False),
            sa.Column("affected_population_json", sa.Text(), nullable=False),
            sa.Column("estimated_impact_conservative", sa.String(64), nullable=False),
            sa.Column("estimated_impact_base", sa.String(64), nullable=False),
            sa.Column("estimated_impact_optimistic", sa.String(64), nullable=False),
            sa.Column("confidence_band", sa.String(16), nullable=False),
            sa.Column("risk_level", sa.String(16), nullable=False),
            sa.Column("selected_action_template", sa.String(64), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("source_content_hash", sa.String(128), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("converted_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "governed_action_drafts" not in existing:
        op.create_table(
            "governed_action_drafts",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("recommendation_id", sa.String(128), nullable=False, index=True),
            sa.Column("action_template", sa.String(64), nullable=False),
            sa.Column("action_template_version", sa.String(16), nullable=False),
            sa.Column("connector_id", sa.String(128), nullable=False),
            sa.Column("process_key", sa.String(128), nullable=False),
            sa.Column("capability", sa.String(128), nullable=False),
            sa.Column("connection_id", sa.String(128), nullable=True),
            sa.Column("arguments_json", sa.Text(), nullable=False),
            sa.Column("constraints_json", sa.Text(), nullable=False),
            sa.Column("required_inputs_json", sa.Text(), nullable=False),
            sa.Column("preflight_spec_json", sa.Text(), nullable=False),
            sa.Column("postcondition_spec_json", sa.Text(), nullable=False),
            sa.Column("compensation_spec_json", sa.Text(), nullable=False),
            sa.Column("execution_classification", sa.String(16), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("converted_run_id", sa.String(128), nullable=True),
            sa.Column("invalidated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    for table in ("governed_action_drafts", "governed_recommendations"):
        if table in existing:
            op.drop_table(table)
