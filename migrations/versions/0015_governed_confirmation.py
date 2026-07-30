"""Add Phase 17 governed-confirmation evidence fields."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0015_governed_confirmation"
down_revision = "0014_execution_permits"
branch_labels = None
depends_on = None


_COLUMNS = {
    "native_plan_json": sa.Text(),
    "state_snapshot_json": sa.Text(),
    "evidence_pack_json": sa.Text(),
    "cleanup_plan_json": sa.Text(),
}


def upgrade() -> None:
    inspector = inspect(op.get_bind())
    if "execution_runs_v2" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("execution_runs_v2")}
    for name, type_ in _COLUMNS.items():
        if name not in existing:
            op.add_column(
                "execution_runs_v2",
                sa.Column(name, type_, nullable=False, server_default="{}"),
            )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "execution_runs_v2" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("execution_runs_v2")}
    for name in reversed(tuple(_COLUMNS)):
        if name in existing:
            op.drop_column("execution_runs_v2", name)
