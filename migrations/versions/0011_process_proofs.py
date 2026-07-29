"""Add Proof of Improvement storage."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0011_process_proofs"
down_revision = "0010_process_replays"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "process_proofs" not in existing:
        op.create_table(
            "process_proofs",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False),
            sa.Column("baseline_replay_id", sa.String(128), nullable=False),
            sa.Column("candidate_replay_id", sa.String(128), nullable=False),
            sa.Column("dataset_version", sa.String(128), nullable=False),
            sa.Column("benchmark_version", sa.String(128), nullable=False),
            sa.Column("metric_comparisons_json", sa.Text(), nullable=False),
            sa.Column("regressions_json", sa.Text(), nullable=False),
            sa.Column("safety_summary_json", sa.Text(), nullable=False),
            sa.Column("reproducibility_summary_json", sa.Text(), nullable=False),
            sa.Column("evidence_refs_json", sa.Text(), nullable=False),
            sa.Column("recommendation", sa.String(32), nullable=False),
            sa.Column("recommendation_basis_json", sa.Text(), nullable=False),
            sa.Column("limitations_json", sa.Text(), nullable=False),
            sa.Column("content_hash", sa.String(128), nullable=False),
            sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        )
        op.create_index("ix_process_proofs_tenant_id", "process_proofs", ["tenant_id"])
        op.create_index("ix_process_proofs_baseline_replay_id", "process_proofs", ["baseline_replay_id"])
        op.create_index("ix_process_proofs_candidate_replay_id", "process_proofs", ["candidate_replay_id"])


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "process_proofs" in existing:
        op.drop_index("ix_process_proofs_candidate_replay_id", table_name="process_proofs")
        op.drop_index("ix_process_proofs_baseline_replay_id", table_name="process_proofs")
        op.drop_index("ix_process_proofs_tenant_id", table_name="process_proofs")
        op.drop_table("process_proofs")
