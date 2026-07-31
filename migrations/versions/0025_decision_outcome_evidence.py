"""Add Spec 92 Workstream D decision-to-outcome evidence bundle."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0025_decision_outcome_evidence"
down_revision = "0024_outcome_measurement"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "decision_outcome_evidence_bundles" not in existing:
        op.create_table(
            "decision_outcome_evidence_bundles",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("recommendation_id", sa.String(128), nullable=False, index=True),
            sa.Column("measurement_plan_id", sa.String(128), nullable=True, index=True),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("manifest_json", sa.Text(), nullable=False),
            sa.Column("missing_resources_json", sa.Text(), nullable=False),
            sa.Column("manifest_hash", sa.String(128), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("chain_hash", sa.String(128), nullable=False),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("sealed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("sealed_by", sa.String(128), nullable=True),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "decision_outcome_evidence_bundles" in existing:
        op.drop_table("decision_outcome_evidence_bundles")
