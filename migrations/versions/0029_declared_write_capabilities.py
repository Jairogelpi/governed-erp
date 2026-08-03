"""Add user-declared field-write capabilities."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0029_declared_write_capabilities"
down_revision = "0028_skill_package_active_uniqueness"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "declared_write_capabilities" not in existing:
        op.create_table(
            "declared_write_capabilities",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("name", sa.String(128), nullable=False),
            sa.Column("target_model", sa.String(128), nullable=False),
            sa.Column("target_field", sa.String(128), nullable=False),
            sa.Column("field_type", sa.String(16), nullable=False),
            sa.Column("minimum_value", sa.String(64), nullable=True),
            sa.Column("maximum_value", sa.String(64), nullable=True),
            sa.Column("allowed_values_json", sa.Text(), nullable=False),
            sa.Column("max_records_per_run", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False, index=True),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("approved_by", sa.String(128), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "declared_write_capabilities" in existing:
        op.drop_table("declared_write_capabilities")
