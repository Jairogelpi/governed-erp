"""Persist the Phase 17.1 confirmation side-effect contract."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


revision = "0016_confirmation_side_effect_contract"
down_revision = "0015_governed_confirmation"
branch_labels = None
depends_on = None


_COLUMNS = {
    "control_contract_json": sa.Text(),
    "control_contract_hash": sa.String(length=128),
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
                sa.Column(name, type_, nullable=False, server_default="{}" if name.endswith("_json") else ""),
            )


def downgrade() -> None:
    inspector = inspect(op.get_bind())
    if "execution_runs_v2" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("execution_runs_v2")}
    for name in reversed(tuple(_COLUMNS)):
        if name in existing:
            op.drop_column("execution_runs_v2", name)
