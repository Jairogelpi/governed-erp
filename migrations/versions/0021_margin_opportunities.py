"""Add Phase 16.6 immutable margin opportunities."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0021_margin_opportunities"
down_revision = "0020_skill_deployment_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "margin_opportunities" not in existing:
        op.create_table(
            "margin_opportunities",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("margin_analysis_id", sa.String(128), nullable=False, index=True),
            sa.Column("snapshot_id", sa.String(128), nullable=False, index=True),
            sa.Column("cause", sa.String(64), nullable=False),
            sa.Column("affected_population_json", sa.Text(), nullable=False),
            sa.Column("evidence_json", sa.Text(), nullable=False),
            sa.Column("impact_conservative", sa.String(64), nullable=False),
            sa.Column("impact_base", sa.String(64), nullable=False),
            sa.Column("impact_optimistic", sa.String(64), nullable=False),
            sa.Column("confidence_band", sa.String(16), nullable=False),
            sa.Column("risk_level", sa.String(16), nullable=False),
            sa.Column("implementation_cost", sa.String(64), nullable=True),
            sa.Column("payback_period_days", sa.Integer(), nullable=True),
            sa.Column("proposed_action", sa.Text(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "margin_opportunities" in existing:
        op.drop_table("margin_opportunities")
