"""Add Phase 18 append-only shadow deployments and evidence."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0017_shadow_mode"
down_revision = "0016_confirmation_side_effect_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "shadow_deployments" not in existing:
        op.create_table(
            "shadow_deployments",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("candidate_id", sa.String(128), nullable=False, index=True),
            sa.Column("proof_id", sa.String(128), nullable=False),
            sa.Column("process_key", sa.String(128), nullable=False, index=True),
            sa.Column("active_version", sa.String(64), nullable=False),
            sa.Column("candidate_version", sa.String(64), nullable=False),
            sa.Column("object_type", sa.String(128), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("agreement_threshold", sa.Float(), nullable=False),
            sa.Column("no_effects", sa.Boolean(), nullable=False),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
    if "shadow_case_results" not in existing:
        op.create_table(
            "shadow_case_results",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("deployment_id", sa.String(128), nullable=False, index=True),
            sa.Column("case_id", sa.String(200), nullable=False, index=True),
            sa.Column("idempotency_key", sa.String(256), nullable=False),
            sa.Column("input_hash", sa.String(128), nullable=False),
            sa.Column("active_decision_json", sa.Text(), nullable=False),
            sa.Column("candidate_decision_json", sa.Text(), nullable=False),
            sa.Column("agreement", sa.Boolean(), nullable=False),
            sa.Column("difference_categories_json", sa.Text(), nullable=False),
            sa.Column("actual_outcome_json", sa.Text(), nullable=True),
            sa.Column("deterministic_hash", sa.String(128), nullable=False),
            sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
            sa.UniqueConstraint(
                "tenant_id",
                "deployment_id",
                "idempotency_key",
                name="uq_shadow_case_tenant_deployment_idempotency",
            ),
        )
    if "shadow_case_reviews" not in existing:
        op.create_table(
            "shadow_case_reviews",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("deployment_id", sa.String(128), nullable=False, index=True),
            sa.Column("shadow_case_result_id", sa.String(128), nullable=False, index=True),
            sa.Column("reviewer_id", sa.String(128), nullable=False),
            sa.Column("label", sa.String(32), nullable=False),
            sa.Column("notes", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    for table in ("shadow_case_reviews", "shadow_case_results", "shadow_deployments"):
        if table in existing:
            op.drop_table(table)
