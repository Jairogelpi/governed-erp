"""Add Spec 93 (Phase 20) ERPRiskBench run/result persistence."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0027_benchmark_runs"
down_revision = "0026_outcome_implementation_cost"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "benchmark_runs" not in existing:
        op.create_table(
            "benchmark_runs",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("dataset_version", sa.String(128), nullable=False),
            sa.Column("dataset_manifest_hash", sa.String(128), nullable=False),
            sa.Column("configurations_json", sa.Text(), nullable=False),
            sa.Column("repeats", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(16), nullable=False),
            sa.Column("created_by", sa.String(128), nullable=False),
            sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
            sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        )
    if "benchmark_case_results" not in existing:
        op.create_table(
            "benchmark_case_results",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("benchmark_run_id", sa.String(128), nullable=False, index=True),
            sa.Column("configuration", sa.String(32), nullable=False),
            sa.Column("case_id", sa.String(128), nullable=False),
            sa.Column("category", sa.String(32), nullable=False),
            sa.Column("repeat_index", sa.Integer(), nullable=False),
            sa.Column("outcome_json", sa.Text(), nullable=False),
            sa.Column("latency_ms", sa.Float(), nullable=True),
            sa.Column("token_cost", sa.Float(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "benchmark_case_results" in existing:
        op.drop_table("benchmark_case_results")
    if "benchmark_runs" in existing:
        op.drop_table("benchmark_runs")
