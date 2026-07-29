"""Add compiled skill package storage (Phase 14)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0013_skill_packages"
down_revision = "0012_replay_case_decision_coverage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "skill_packages" not in existing:
        op.create_table(
            "skill_packages",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("candidate_id", sa.String(128), nullable=False),
            sa.Column("proof_id", sa.String(128), nullable=False),
            sa.Column("process_key", sa.String(128), nullable=False),
            sa.Column("candidate_version", sa.String(64), nullable=False),
            sa.Column("connector_id", sa.String(128), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("package_json", sa.Text(), nullable=False),
            sa.Column("validation_result_json", sa.Text(), nullable=False),
            sa.Column("package_hash", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_skill_packages_tenant_id", "skill_packages", ["tenant_id"])
        op.create_index("ix_skill_packages_candidate_id", "skill_packages", ["candidate_id"])
        op.create_index("ix_skill_packages_process_key", "skill_packages", ["process_key"])


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "skill_packages" in existing:
        op.drop_index("ix_skill_packages_process_key", table_name="skill_packages")
        op.drop_index("ix_skill_packages_candidate_id", table_name="skill_packages")
        op.drop_index("ix_skill_packages_tenant_id", table_name="skill_packages")
        op.drop_table("skill_packages")
