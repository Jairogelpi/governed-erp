"""Add historical replay and replay case storage."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0010_process_replays"
down_revision = "0009_drop_retired_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "process_replays" not in existing:
        op.create_table(
            "process_replays",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("process_key", sa.String(128), nullable=False),
            sa.Column("version", sa.String(64), nullable=False),
            sa.Column("object_type", sa.String(128), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("policy_version", sa.String(64), nullable=False),
            sa.Column("connector_simulator_version", sa.String(128), nullable=False),
            sa.Column("case_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("frozen_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_process_replays_tenant_id", "process_replays", ["tenant_id"])
        op.create_index("ix_process_replays_process_key", "process_replays", ["process_key"])

    if "process_replay_cases" not in existing:
        op.create_table(
            "process_replay_cases",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("replay_id", sa.String(128), nullable=False),
            sa.Column("case_id", sa.String(200), nullable=False),
            sa.Column("status", sa.String(32), nullable=False),
            sa.Column("decision_trace_json", sa.Text(), nullable=False),
            sa.Column("predicted_effects_json", sa.Text(), nullable=False),
            sa.Column("safety_violations_json", sa.Text(), nullable=False),
            sa.Column("regressions_json", sa.Text(), nullable=False),
            sa.Column("metrics_json", sa.Text(), nullable=False),
            sa.Column("deterministic_trace_hash", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_process_replay_cases_tenant_id", "process_replay_cases", ["tenant_id"])
        op.create_index("ix_process_replay_cases_replay_id", "process_replay_cases", ["replay_id"])


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "process_replay_cases" in existing:
        op.drop_index("ix_process_replay_cases_replay_id", table_name="process_replay_cases")
        op.drop_index("ix_process_replay_cases_tenant_id", table_name="process_replay_cases")
        op.drop_table("process_replay_cases")
    if "process_replays" in existing:
        op.drop_index("ix_process_replays_process_key", table_name="process_replays")
        op.drop_index("ix_process_replays_tenant_id", table_name="process_replays")
        op.drop_table("process_replays")
