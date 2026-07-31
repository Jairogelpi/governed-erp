"""Add Phase 19 append-only skill deployment lifecycle events."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0020_skill_deployment_lifecycle"
down_revision = "0019_decision_intelligence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "skill_deployment_events" not in existing:
        op.create_table(
            "skill_deployment_events",
            sa.Column("id", sa.String(128), primary_key=True),
            sa.Column("tenant_id", sa.String(128), nullable=False, index=True),
            sa.Column("process_key", sa.String(128), nullable=False, index=True),
            sa.Column("skill_package_id", sa.String(128), nullable=False, index=True),
            sa.Column("event_type", sa.String(32), nullable=False),
            sa.Column("from_status", sa.String(32), nullable=False),
            sa.Column("to_status", sa.String(32), nullable=False),
            sa.Column("shadow_deployment_id", sa.String(128), nullable=True),
            sa.Column("reason", sa.Text(), nullable=False),
            sa.Column("actor", sa.String(128), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        )


def downgrade() -> None:
    existing = set(inspect(op.get_bind()).get_table_names())
    if "skill_deployment_events" in existing:
        op.drop_table("skill_deployment_events")
