"""Add Execution Permit runtime storage (Phase 15)."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0014_execution_permits"
down_revision = "0013_skill_packages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())

    if "execution_runs_v2" not in existing:
        op.create_table(
            "execution_runs_v2",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("actor_id", sa.String(128), nullable=False),
            sa.Column("connection_id", sa.String(128), nullable=False),
            sa.Column("connector_id", sa.String(128), nullable=False),
            sa.Column("skill_package_id", sa.String(128), nullable=False),
            sa.Column("process_version_id", sa.String(128), nullable=False),
            sa.Column("skill_version_id", sa.String(128), nullable=False),
            sa.Column("capability", sa.String(128), nullable=False),
            sa.Column("action_plan_json", sa.Text(), nullable=False),
            sa.Column("operation_hash", sa.String(128), nullable=False),
            sa.Column("native_plan_hash", sa.String(128), nullable=False),
            sa.Column("state_snapshot_hash", sa.String(128), nullable=False),
            sa.Column("capability_allowlist_json", sa.Text(), nullable=False),
            sa.Column("approval_ids_json", sa.Text(), nullable=False),
            sa.Column("idempotency_key", sa.String(256), nullable=False),
            sa.Column("signature", sa.String(256), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("single_use", sa.Boolean(), nullable=False),
            sa.Column("verification_result_json", sa.Text(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("executed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_execution_runs_v2_tenant_id", "execution_runs_v2", ["tenant_id"])
        op.create_index("ix_execution_runs_v2_skill_package_id", "execution_runs_v2", ["skill_package_id"])
        op.create_index("ix_execution_runs_v2_idempotency_key", "execution_runs_v2", ["idempotency_key"])

    if "execution_approvals" not in existing:
        op.create_table(
            "execution_approvals",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("actor_id", sa.String(128), nullable=False),
            sa.Column("scope", sa.String(256), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("used_by_run_id", sa.String(128), nullable=True),
        )
        op.create_index("ix_execution_approvals_tenant_id", "execution_approvals", ["tenant_id"])

    if "execution_kill_switches" not in existing:
        op.create_table(
            "execution_kill_switches",
            sa.Column("tenant_id", sa.String(128), primary_key=True),
            sa.Column("active", sa.Boolean(), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "execution_kill_switches" in existing:
        op.drop_table("execution_kill_switches")
    if "execution_approvals" in existing:
        op.drop_index("ix_execution_approvals_tenant_id", table_name="execution_approvals")
        op.drop_table("execution_approvals")
    if "execution_runs_v2" in existing:
        op.drop_index("ix_execution_runs_v2_idempotency_key", table_name="execution_runs_v2")
        op.drop_index("ix_execution_runs_v2_skill_package_id", table_name="execution_runs_v2")
        op.drop_index("ix_execution_runs_v2_tenant_id", table_name="execution_runs_v2")
        op.drop_table("execution_runs_v2")
