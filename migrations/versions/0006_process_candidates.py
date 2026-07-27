"""Add process candidate branching storage."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0006_process_candidates"
down_revision = "0005_process_version_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "process_candidates" in existing:
        return
    op.create_table(
        "process_candidates",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("process_key", sa.String(128), nullable=False),
        sa.Column("base_version", sa.String(64), nullable=False),
        sa.Column("candidate_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("changes_json", sa.Text(), nullable=False),
        sa.Column("evidence_json", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("process_key", "candidate_version", name="uq_process_candidate_version"),
    )
    op.create_index("ix_process_candidates_process_key", "process_candidates", ["process_key"])


def downgrade() -> None:
    op.drop_index("ix_process_candidates_process_key", table_name="process_candidates")
    op.drop_table("process_candidates")
